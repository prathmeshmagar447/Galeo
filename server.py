import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database model
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    filename = db.Column(db.String(500))
    s3_key = db.Column(db.String(500))


with app.app_context():
    db.create_all()

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


@app.route("/")
def index():
    images = Image.query.all()
    current_year = datetime.now().year
    return render_template("index.html", images=images, current_year=current_year)


# Upload to S3
def upload_to_s3(file):
    try:
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        s3_key = (
            f"uploads/{timestamp}-{uuid.uuid4()}{file_ext}" 
        )

        s3.upload_fileobj(file, S3_BUCKET, s3_key, ExtraArgs={"ACL": "public-read"})

        file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        return file_url, s3_key
    except ClientError as e:
        flash(f"Error uploading to S3: {e}", "danger")
        print(f"Error uploading to S3: {e}")
        return None, None


# Delete from S3
def delete_from_s3(s3_key):
    if not s3_key:
        return
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)
    except ClientError as e:
        print("Error deleting from S3:", e)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    current_year = datetime.now().year
    if request.method == "POST":
        title = request.form["title"]
        file = request.files["file"]
        if file:
            s3_url, s3_key = upload_to_s3(file)
            if s3_url:
                img = Image(title=title, filename=s3_url, s3_key=s3_key)
                db.session.add(img)
                db.session.commit()
                flash("Image uploaded successfully!", "success")
                return redirect(url_for("index"))
            else:
                flash("Error uploading image", "danger")

        else:
            flash("Please select a file", "warning")
    return render_template("upload.html", current_year=current_year)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    img = Image.query.get_or_404(id)
    current_year = datetime.now().year
    if request.method == "POST":
        img.title = request.form["title"]
        db.session.commit()
        flash("Image title updated!", "success")
        return redirect(url_for("index"))
    return render_template("edit.html", image=img, current_year=current_year)


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    img = Image.query.get_or_404(id)
    delete_from_s3(img.s3_key)
    db.session.delete(img)
    db.session.commit()
    flash("Image deleted!", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
