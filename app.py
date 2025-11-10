import os
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import boto3

# Supabase
from supabase import create_client

# CLIP imports
import torch
import pickle
import numpy as np
from PIL import Image as PILImage
from transformers import AutoProcessor, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///gallery.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session time
session_minutes = int(os.getenv("PERMANENT_SESSION_LIFETIME_MINUTES", "30"))
app.permanent_session_lifetime = timedelta(minutes=session_minutes)

db = SQLAlchemy(app)

# --- CLIP Model Loading ---
logger.info("Loading CLIP model...")
try:
    CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
    device = "cuda" if torch.cuda.is_available() else "cpu"

    clip_processor = AutoProcessor.from_pretrained(CLIP_MODEL_ID)
    clip_model = AutoModel.from_pretrained(CLIP_MODEL_ID).to(device)
    logger.info(f"CLIP model loaded successfully on device: {device}")
except Exception as e:
    logger.error(f"Failed to load CLIP model: {e}")
    raise
# ---------------------------

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# AWS S3 setup
S3_BUCKET = os.getenv("AWS_S3_BUCKET")
S3_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

s3 = boto3.client(
    "s3",
    region_name=S3_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# ------------------ MODELS ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supabase_id = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    images = db.relationship("Image", backref="user", lazy=True)


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    file_url = db.Column(db.String(500))
    s3_key = db.Column(db.String(500))
    user_id = db.Column(db.String(200), db.ForeignKey("user.supabase_id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    embedding = db.Column(db.BLOB, nullable=True)  # To store the pickled vector


with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


# ------------------ HELPERS ------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "access_token" not in session or "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def get_current_user():
    if "user_id" in session:
        return {"id": session["user_id"], "email": session["email"]}
    return None


def upload_to_s3(file, filename=None):
    try:
        if filename is None:
            filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1]
        s3_key = f"uploads/{uuid.uuid4()}{ext}"
        file.seek(0)
        s3.upload_fileobj(file, S3_BUCKET, s3_key, ExtraArgs={"ACL": "public-read"})
        url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"S3 Upload successful: {s3_key}")
        return url, s3_key
    except Exception as e:
        logger.error(f"S3 upload failed for {filename}: {e}")
        raise Exception(f"Failed to upload file to S3: {str(e)}")


def generate_embedding(image_file):
    """
    Generates a CLIP embedding for a given image file and returns it as a serialized pickle BLOB.
    """
    try:
        # We must seek(0) in case the file was read before (e.g., by upload_to_s3)
        image_file.seek(0)

        # Open the image using PIL
        image = PILImage.open(image_file)

        # Process the image for CLIP
        inputs = clip_processor(images=image, return_tensors="pt").to(device)

        # Generate embedding
        with torch.no_grad():  # Disables gradient calculation for faster inference
            image_features = clip_model.get_image_features(**inputs)

        # Move vector to CPU, convert to numpy array, and serialize using pickle
        vector = image_features.cpu().numpy()
        serialized_vector = pickle.dumps(vector)

        return serialized_vector
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return None


def generate_text_embedding(text):
    """
    Generates a CLIP embedding for a given text string and returns it as a numpy array.
    """
    try:
        # Process the text for CLIP
        inputs = clip_processor(text=[text], return_tensors="pt").to(device)

        # Generate embedding
        with torch.no_grad():  # Disables gradient calculation for faster inference
            text_features = clip_model.get_text_features(**inputs)

        # Move vector to CPU and convert to numpy array
        vector = text_features.cpu().numpy()

        return vector
    except Exception as e:
        logger.error(f"Failed to generate text embedding: {e}")
        return None


# ------------------ CONTEXT PROCESSORS ------------------
@app.context_processor
def inject_current_user():
    return dict(current_user=get_current_user())

# ------------------ ROUTES ------------------
@app.route("/")
@login_required
def gallery():
    user = get_current_user()
    search_query = request.args.get("q", "").strip()

    if search_query:
        # Perform semantic search
        text_embedding = generate_text_embedding(search_query)
        if text_embedding is None:
            flash("Failed to process search query.", "danger")
            return redirect(url_for("gallery"))

        # Get all user's images
        images = Image.query.filter_by(user_id=user["id"]).all()

        # Calculate similarities
        image_similarities = []
        for img in images:
            if img.embedding:
                try:
                    # Deserialize the image embedding
                    img_embedding = pickle.loads(img.embedding)
                    # Calculate cosine similarity
                    similarity = cosine_similarity(text_embedding, img_embedding)[0][0]
                    image_similarities.append((img, similarity))
                except Exception as e:
                    logger.error(f"Failed to process embedding for image {img.id}: {e}")
                    continue

        # Sort by similarity (highest first)
        image_similarities.sort(key=lambda x: x[1], reverse=True)
        images = [img for img, _ in image_similarities]

        return render_template("gallery.html", images=images, search_query=search_query)
    else:
        # Show all images ordered by creation date
        images = Image.query.filter_by(user_id=user["id"]).order_by(Image.created_at.desc()).all()
        return render_template("gallery.html", images=images)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            result = supabase.auth.sign_up({"email": email, "password": password})
            if result.user:
                u = User(supabase_id=result.user.id, email=email)
                db.session.add(u)
                db.session.commit()
                logger.info(f"New user signed up: {email}")
                flash("Signup successful! Please log in.", "success")
                return redirect(url_for("login"))
            flash("Signup failed.", "danger")
        except Exception as e:
            logger.error(f"Signup error for {email}: {e}")
            flash("Signup failed. Please try again.", "danger")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.session:
                session["access_token"] = res.session.access_token
                session["user_id"] = res.user.id
                session["email"] = email
                session.permanent = True
                flash("Logged in!", "success")
                return redirect(url_for("gallery"))
        except Exception:
            flash("Login failed.", "danger")
    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        try:
            supabase.auth.reset_password_for_email(email)
            flash("If an account with that email exists, a password reset link has been sent.", "info")
        except Exception as e:
            flash(f"Error sending password reset link: {e}", "danger")
    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    user = get_current_user()
    if request.method == "POST":
        files = request.files.getlist("files")
        titles = request.form.getlist("title") # Get a list of titles, if provided

        if not files or all(f.filename == "" for f in files):
            flash("No files selected.", "warning")
            return redirect(url_for("upload"))

        uploaded_count = 0
        try:
            for i, file in enumerate(files):
                if file and file.filename != "":
                    title = titles[i] if i < len(titles) and titles[i] else "Untitled" # Use provided title or default

                    # Read file content once to avoid multiple seeks on potentially closed file
                    file.seek(0)
                    file_content = file.read()
                    filename = secure_filename(file.filename)

                    # 1. Upload to S3
                    from io import BytesIO
                    file_for_s3 = BytesIO(file_content)
                    file_for_s3.seek(0)
                    url, s3_key = upload_to_s3(file_for_s3, filename)

                    # 2. Generate embedding
                    file_for_embedding = BytesIO(file_content)
                    file_for_embedding.seek(0)
                    serialized_embedding = generate_embedding(file_for_embedding)

                    # 3. Create the Image object with the new embedding data
                    img = Image(
                        title=title,
                        file_url=url,
                        s3_key=s3_key,
                        user_id=user["id"],
                        embedding=serialized_embedding  # <-- ADDED
                    )
                    db.session.add(img)
                    uploaded_count += 1

            if uploaded_count > 0:
                db.session.commit()
                logger.info(f"User {user['email']} uploaded {uploaded_count} images")
                flash(f"{uploaded_count} image(s) uploaded!", "success")
            else:
                flash("No valid images to upload.", "warning")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Upload failed for user {user['email']}: {e}")
            flash("Upload failed. Please try again.", "danger")

        return redirect(url_for("gallery"))
    return render_template("upload.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    try:
        img = Image.query.get_or_404(id)
        user = get_current_user()
        if img.user_id != user["id"]:
            flash("Not allowed.", "danger")
            return redirect(url_for("gallery"))
        if request.method == "POST":
            new_title = request.form["title"]
            img.title = new_title
            db.session.commit()
            logger.info(f"User {user['email']} updated image {id} title")
            flash("Image title updated.", "success")
            return redirect(url_for("gallery"))
        return render_template("edit.html", image=img)
    except Exception as e:
        logger.error(f"Edit failed for image {id}: {e}")
        db.session.rollback()
        flash("Failed to update image. Please try again.", "danger")
        return redirect(url_for("gallery"))


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    try:
        img = Image.query.get_or_404(id)
        user = get_current_user()
        if img.user_id != user["id"]:
            flash("Not allowed.", "danger")
            return redirect(url_for("gallery"))

        # Delete from S3
        s3.delete_object(Bucket=S3_BUCKET, Key=img.s3_key)
        # Delete from database
        db.session.delete(img)
        db.session.commit()
        logger.info(f"User {user['email']} deleted image {id}")
        flash("Deleted.", "info")
        return redirect(url_for("gallery"))
    except Exception as e:
        logger.error(f"Delete failed for image {id}: {e}")
        db.session.rollback()
        flash("Failed to delete image. Please try again.", "danger")
        return redirect(url_for("gallery"))


if __name__ == "__main__":
    app.run()
