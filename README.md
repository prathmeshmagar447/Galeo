# Image Gallery Application

This is a Flask-based image gallery application that allows users to upload, view, edit, and delete images. Images are stored on AWS S3, and their metadata (title, S3 URL, S3 key) is stored in a SQLite database.

## Features

- **Image Upload:** Upload images with a title.
- **Image Display:** View all uploaded images in a gallery.
- **Edit Image:** Update the title of an existing image.
- **Delete Image:** Remove images from both the database and AWS S3.

## Technologies Used

- **Flask:** Web framework for Python.
- **Flask-SQLAlchemy:** ORM for database interactions (SQLite).
- **Boto3:** AWS SDK for Python, used for S3 integration.
- **python-dotenv:** For loading environment variables.
- **Werkzeug:** For secure filename handling.

## Setup and Installation

### Prerequisites

- Python 3.x
- AWS Account with S3 bucket configured
- AWS Access Key ID and Secret Access Key

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/prathmeshmagar447/Galeo.git
   cd Galeo
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file:**
   Create a file named `.env` in the root directory of the project and add the following environment variables:

   ```
   FLASK_SECRET_KEY="your_secret_key_for_flask_sessions"
   AWS_S3_BUCKET="your_s3_bucket_name"
   AWS_REGION="your_aws_region_e.g._us-east-1"
   AWS_ACCESS_KEY_ID="your_aws_access_key_id"
   AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
   ```
   Replace the placeholder values with your actual AWS credentials and desired Flask secret key.

5. **Initialize the database:**
   The application will automatically create the `gallery.db` file and the `Image` table when it runs for the first time.

## Running the Application

1. **Activate your virtual environment (if not already active):**
   ```bash
   source venv/bin/activate
   ```

2. **Run the Flask application:**
   ```bash
   python app.py
   ```

3. **Access the application:**
   Open your web browser and navigate to `http://127.0.0.1:5000/`.

## Project Structure

```
.
├── .env                  # Environment variables
├── app.py                # Main Flask application
├── README.md             # Project README
├── requirements.txt      # Python dependencies
├── instance/             # Flask instance folder (contains gallery.db)
├── static/
│   └── style.css         # CSS for styling
└── templates/
    ├── edit.html         # Template for editing image titles
    ├── index.html        # Main gallery page
    └── upload.html       # Template for uploading images
