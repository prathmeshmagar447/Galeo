import os
import uuid
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Supabase client
from supabase import create_client  # supabase-py

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "dev-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session lifetime (in minutes)
session_minutes = int(os.getenv("PERMANENT_SESSION_LIFETIME_MINUTES", "30"))
app.permanent_session_lifetime = timedelta(minutes=session_minutes)

db = SQLAlchemy(app)

# Supabase client (server-side)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Please set SUPABASE_URL and SUPABASE_KEY in environment")

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

# ---------- Database models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Supabase user id (UUID string)
    supabase_id = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    username = db.Column(db.String(120), nullable=True)
    # You can keep track if you want — but Supabase stores confirmation state
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship("Image", backref="user", lazy=True)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    filename = db.Column(db.String(500))
    s3_key = db.Column(db.String(500))
    # store Supabase user id (string)
    user_id = db.Column(db.String(200), db.ForeignKey("user.supabase_id"))

with app.app_context():
    db.create_all()

# ---------- Helpers ----------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "access_token" not in session or "user_id" not in session:
            flash("Please log in to access this page", "warning")
            return redirect(url_for("login"))
        # optionally verify access token against Supabase to ensure it's still valid
        if not verify_token(session.get("access_token")):
            # token invalid or expired — clear session and require login
            session.clear()
            flash("Session expired — please log in again", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def verify_token(access_token: str) -> bool:
    """Verify an access token with Supabase. Returns user dict if valid, else False.

    NOTE: supabase.auth.get_user(access_token) is common; if your supabase-py version differs,
    you may need to call: supabase.auth.api.get_user(access_token) or use REST JWT verify.
    """
    if not access_token:
        return False
    try:
        res = supabase.auth.get_user(access_token)
        return bool(res and res.user)
    except Exception:
        return False

def get_current_user():
    """Return a lightweight user object from session or None"""
    if "user_id" in session:
        return {"id": session.get("user_id"), "email": session.get("email")}
    return None

# ---------- S3 helpers ----------
def upload_to_s3(file):
    try:
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        s3_key = f"uploads/{timestamp}-{uuid.uuid4()}{file_ext}"
        file.seek(0)
        s3.upload_fileobj(file, S3_BUCKET, s3_key, ExtraArgs={"ACL": "public-read"})
        file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        return file_url, s3_key
    except ClientError as e:
        app.logger.error("Error uploading to S3: %s", e)
        return None, None

def delete_from_s3(s3_key):
    if not s3_key:
        return
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        app.logger.error("Error deleting from S3: %s", e)

# ---------- Routes: Auth ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        username = request.form.get("username") or None

        if not email or not password:
            flash("Email and password required", "warning")
            return redirect(url_for("signup"))

        try:
            result = supabase.auth.sign_up({"email": email, "password": password})

            if result.user:
                supabase_id = result.user.id
                existing = User.query.filter_by(supabase_id=supabase_id).first()
                if not existing:
                    u = User(supabase_id=supabase_id, email=email, username=username)
                    db.session.add(u)
                    db.session.commit()
            else:
                flash(f"Sign up error: {result.session.user.email if result.session and result.session.user else 'Unknown error'}", "danger")
                return redirect(url_for("signup"))

            flash("Signup successful — check your email to confirm your account (if enabled).", "info")
            return redirect(url_for("login"))
        except Exception as e:
            app.logger.exception(e)
            flash("Error signing up: " + str(e), "danger")
            return redirect(url_for("signup"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            flash("Email and password required", "warning")
            return redirect(url_for("login"))

        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})

            if res.session and res.user:
                access_token = res.session.access_token
                supabase_id = res.user.id
            else:
                flash("Login failed: Invalid credentials or unconfirmed email.", "danger")
                return redirect(url_for("login"))

            # Persist session in Flask session cookie
            session.clear()
            session["access_token"] = access_token
            session["user_id"] = supabase_id
            session["email"] = email
            session.permanent = True  # use app.permanent_session_lifetime
            flash("Logged in successfully", "success")
            return redirect(url_for("index"))
        except Exception as e:
            app.logger.exception("Login error: %s", e)
            flash("Login failed: " + str(e), "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    # Optionally: revoke session at Supabase side using refresh token — supabase-py may support
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for("login"))

# Password reset request
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Please provide your email", "warning")
            return redirect(url_for("forgot"))
        try:
            # This triggers Supabase to send a password reset email with a link.
            res = supabase.auth.reset_password_for_email(email=email, redirect_to=url_for("reset_redirect", _external=True))
            flash("If that email exists, a password reset link has been sent.", "info")
            return redirect(url_for("login"))
        except Exception as e:
            app.logger.exception(e)
            flash("Error sending password reset email: " + str(e), "danger")
            return redirect(url_for("forgot"))
    return render_template("forgot.html")

# Supabase password reset link will likely redirect to your app or to the Supabase-hosted page.
# If you configure redirect_to to a route on your app, handle it here:
@app.route("/reset-redirect")
def reset_redirect():
    # Supabase may include access_token or oobCode-like token in query params
    # You can capture token and present a UI to set new password, then call update_user
    token = request.args.get("access_token") or request.args.get("token")
    # render a page that includes the token in a hidden form field that posts to /reset
    return render_template("reset.html", token=token)

@app.route("/reset", methods=["POST"])
def reset():
    # Called after the user submits new password from reset page
    token = request.form.get("token") or request.args.get("token")
    new_password = request.form.get("password")
    if not token or not new_password:
        flash("Invalid reset request", "danger")
        return redirect(url_for("forgot"))

    try:
        res = supabase.auth.update_user(password=new_password)
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("login"))
    except Exception as e:
        app.logger.exception("Password reset error: %s", e)
        flash("Could not reset password — try the link again or request another reset.", "danger")
        return redirect(url_for("forgot"))

# ---------- Routes: Application (protected) ----------
@app.route("/")
@login_required
def index():
    user = get_current_user()
    images = Image.query.filter_by(user_id=user["id"]).all()
    current_year = datetime.now().year
    return render_template("index.html", images=images, current_year=current_year)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    current_year = datetime.now().year
    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("file")
        if not file:
            flash("Please select a file", "warning")
            return redirect(url_for("upload"))

        # Optional: validate allowed extensions
        allowed = {"png", "jpg", "jpeg", "gif"}
        if "." in file.filename:
            ext = file.filename.rsplit(".", 1)[1].lower()
            if ext not in allowed:
                flash("Unsupported file type", "warning")
                return redirect(url_for("upload"))

        s3_url, s3_key = upload_to_s3(file)
        if s3_url:
            user = get_current_user()
            img = Image(title=title, filename=s3_url, s3_key=s3_key, user_id=user["id"])
            db.session.add(img)
            db.session.commit()
            flash("Image uploaded successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Error uploading image", "danger")
    return render_template("upload.html", current_year=current_year)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    img = Image.query.get_or_404(id)
    # Ensure the image belongs to current user
    user = get_current_user()
    if img.user_id != user["id"]:
        abort(403)
    if request.method == "POST":
        img.title = request.form.get("title")
        db.session.commit()
        flash("Image title updated!", "success")
        return redirect(url_for("index"))
    current_year = datetime.now().year
    return render_template("edit.html", image=img, current_year=current_year)

@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    img = Image.query.get_or_404(id)
    user = get_current_user()
    if img.user_id != user["id"]:
        abort(403)
    delete_from_s3(img.s3_key)
    db.session.delete(img)
    db.session.commit()
    flash("Image deleted!", "info")
    return redirect(url_for("index"))

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
