#!/bin/bash

APP_DIR="/var/www/Galeo"
APP_NAME="app" # Assuming your Flask app instance is named 'app' in 'app.py'
echo "Deleting old app directory if it exists..."
sudo rm -rf $APP_DIR

echo "Creating app directory: $APP_DIR"
sudo mkdir -p $APP_DIR

echo "Moving files from /home/ubuntu/ to $APP_DIR"
sudo mv /home/ubuntu/* $APP_DIR/

# Navigate to the app directory
cd $APP_DIR

# Rename 'env' file to '.env' if it exists (from GitHub Actions)
if [ -f env ]; then
    sudo mv env .env
fi

# Load environment variables
source .env

echo "Updating apt-get and installing python3-venv"
sudo apt-get update
sudo apt-get install -y python3-venv

echo "Setting up Python virtual environment and installing dependencies"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Stopping any existing Gunicorn process..."
sudo pkill gunicorn || true # '|| true' prevents script from exiting if no gunicorn process is found

echo "Starting Gunicorn with the Flask application 🚀"
# Assuming your Flask app instance is named 'app' in 'app.py'
# Binding to 0.0.0.0:8000 to make it accessible.
# WARNING: Exposing Gunicorn directly to the internet is generally not recommended for production.
# Consider using a proper reverse proxy (like Nginx or Apache) or a firewall for security.
sudo gunicorn --workers 3 --bind 0.0.0.0:8000 'app:app' --daemon
echo "Gunicorn started."
