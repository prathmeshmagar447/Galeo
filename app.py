import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import boto3

# Supabase
from supabase import create_client

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///gallery.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session time
session_minutes = int(os.getenv("PERMANENT_SESSION_LIFETIME_MINUTES", "30"))
app.permanent_session_lifetime = timedelta(minutes=session_minutes)

db = SQLAlchemy(app)

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


with app.app_context():
    db.create_all()


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


def upload_to_s3(file):
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1]
    s3_key = f"uploads/{uuid.uuid4()}{ext}"
    file.seek(0)
    s3.upload_fileobj(file, S3_BUCKET, s3_key, ExtraArgs={"ACL": "public-read"})
    url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
    print(f"S3 Upload URL: {url}, S3 Key: {s3_key}") # Debug print
    return url, s3_key


# ------------------ CONTEXT PROCESSORS ------------------
@app.context_processor
def inject_current_user():
    return dict(current_user=get_current_user())

# ------------------ ROUTES ------------------
@app.route("/")
@login_required
def gallery():
    user = get_current_user()
    images = Image.query.filter_by(user_id=user["id"]).order_by(Image.created_at.desc()).all()
    return render_template("gallery.html", images=images)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        result = supabase.auth.sign_up({"email": email, "password": password})
        if result.user:
            u = User(supabase_id=result.user.id, email=email)
            db.session.add(u)
            db.session.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for("login"))
        flash("Signup failed.", "danger")
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
        for i, file in enumerate(files):
            if file and file.filename != "":
                title = titles[i] if i < len(titles) and titles[i] else "Untitled" # Use provided title or default
                url, s3_key = upload_to_s3(file)
                img = Image(title=title, file_url=url, s3_key=s3_key, user_id=user["id"])
                db.session.add(img)
                uploaded_count += 1
        
        if uploaded_count > 0:
            db.session.commit()
            flash(f"{uploaded_count} image(s) uploaded!", "success")
        else:
            flash("No valid images to upload.", "warning")

        return redirect(url_for("gallery"))
    return render_template("upload.html")


@app.route("/debug-gallery")
@login_required
def debug_gallery():
    user = get_current_user()
    images = Image.query.filter_by(user_id=user["id"]).order_by(Image.created_at.desc()).all()
    for img in images:
        print(f"Debug Gallery - Image Title: {img.title}, File URL: {img.file_url}")
    return render_template("gallery.html", images=images)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    img = Image.query.get_or_404(id)
    user = get_current_user()
    if img.user_id != user["id"]:
        flash("Not allowed.", "danger")
        return redirect(url_for("gallery"))
    if request.method == "POST":
        new_title = request.form["title"]
        img.title = new_title
        db.session.commit()
        flash("Image title updated.", "success")
        return redirect(url_for("gallery"))
    return render_template("edit.html", image=img)


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    img = Image.query.get_or_404(id)
    user = get_current_user()
    if img.user_id != user["id"]:
        flash("Not allowed.", "danger")
        return redirect(url_for("gallery"))
    s3.delete_object(Bucket=S3_BUCKET, Key=img.s3_key)
    db.session.delete(img)
    db.session.commit()
    flash("Deleted.", "info")
    return redirect(url_for("gallery"))


if __name__ == "__main__":
    app.run(debug=True, port=8000)
