# Galeo - AI-Powered Semantic Image Gallery

![Galeo Logo](static/images/logo.svg)

**Galeo** is an advanced Flask-based image gallery application featuring AI-powered semantic search using OpenAI's CLIP model. Upload images and find them using natural language descriptions rather than just titles or filenames.

## ✨ Features

### Core Functionality
- **📤 Image Upload**: Upload multiple images with custom titles
- **🖼️ Gallery View**: Beautiful responsive grid layout for image browsing
- **✏️ Edit Images**: Update image titles and metadata
- **🗑️ Delete Images**: Remove images from both database and cloud storage

### 🚀 AI-Powered Features
- **🔍 Semantic Search**: Find images using natural language descriptions
- **🧠 CLIP Integration**: Uses OpenAI's CLIP model for image understanding
- **📊 Cosine Similarity**: Advanced ranking based on visual and semantic similarity
- **🎯 Smart Matching**: Search for "a red sports car" and find relevant images

### User Experience
- **🎨 Modern UI**: Dark theme with glassmorphism effects
- **📱 Responsive Design**: Works perfectly on desktop and mobile
- **🔒 User Authentication**: Secure login/signup with Supabase
- **☁️ Cloud Storage**: Images stored securely on AWS S3

## 🛠️ Technologies Used

### Backend
- **Flask 3.1.2**: Modern Python web framework
- **Flask-SQLAlchemy 3.1.1**: Database ORM with SQLite
- **Transformers 4.57.1**: Hugging Face transformers for CLIP
- **PyTorch 2.9.0**: Deep learning framework
- **Scikit-learn 1.7.2**: Machine learning for similarity calculations

### Frontend
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript**: Interactive gallery with modal previews
- **Responsive Design**: Mobile-first approach

### Infrastructure
- **AWS S3**: Cloud storage for images
- **Supabase**: Authentication and user management
- **SQLite**: Lightweight database for metadata

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- AWS Account with S3 bucket
- Supabase project (optional, for authentication)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/prathmeshmagar447/Galeo.git
   cd Galeo
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   Create a `.env` file in the root directory:
   ```env
   FLASK_SECRET_KEY=your_secret_key_here
   AWS_S3_BUCKET=your_s3_bucket_name
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_key
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   Navigate to `http://127.0.0.1:5000/`

## 🎯 How Semantic Search Works

1. **Upload Phase**: When you upload an image, CLIP analyzes its visual content and creates a mathematical representation (embedding)
2. **Search Phase**: When you search with text like "beach sunset", CLIP creates an embedding for your query
3. **Matching**: The system calculates similarity between your search embedding and all image embeddings
4. **Ranking**: Images are ranked by similarity score and displayed in order of relevance

### Example Searches
- `"red sports car"` → Finds images of red cars
- `"mountain landscape"` → Finds scenic mountain photos
- `"person smiling"` → Finds portrait photos with smiles
- `"modern architecture"` → Finds building and structure photos

## 📁 Project Structure

```
galeo/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies with versions
├── .gitignore               # Git ignore rules
├── instance/                # Flask instance folder
│   └── gallery.db           # SQLite database
├── static/                  # Static assets
│   ├── css/
│   │   └── style.css        # Custom styles
│   └── images/              # Static images
│       ├── logo.svg
│       └── favicon.svg
├── templates/               # Jinja2 templates
│   ├── base.html            # Base template with header
│   ├── gallery.html         # Main gallery page
│   ├── upload.html          # Upload form
│   ├── edit.html            # Edit image form
│   ├── login.html           # Login page
│   ├── signup.html          # Signup page
│   └── forgot_password.html # Password reset
└── README.md                # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions | Yes |
| `AWS_S3_BUCKET` | Your S3 bucket name | Yes |
| `AWS_REGION` | AWS region (e.g., us-east-1) | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `SUPABASE_URL` | Supabase project URL | No |
| `SUPABASE_KEY` | Supabase API key | No |

### AWS S3 Setup

1. Create an S3 bucket in your AWS account
2. Configure CORS for web access:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": []
     }
   ]
   ```
3. Create an IAM user with S3 permissions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI CLIP**: For the amazing vision-language model
- **Hugging Face**: For the transformers library
- **Flask Community**: For the excellent web framework
- **Tailwind CSS**: For the beautiful styling system

---

**Made with ❤️ and AI**
