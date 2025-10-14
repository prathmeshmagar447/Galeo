#!/bin/bash

APP_DIR="/var/www/Galeo"
APP_NAME="app" # Assuming your Flask app instance is named 'app' in 'app.py'
APP_SOCKET="$APP_DIR/$APP_NAME.sock"

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

# Update and install Nginx if not already installed
if ! command -v nginx > /dev/null; then
    echo "Installing Nginx"
    sudo apt-get update
    sudo apt-get install -y nginx
fi

# Configure Nginx to act as a reverse proxy if not already configured
NGINX_CONF="/etc/nginx/sites-available/$APP_NAME"
NGINX_SYMLINK="/etc/nginx/sites-enabled/$APP_NAME"

if [ ! -f $NGINX_CONF ]; then
    echo "Configuring Nginx reverse proxy"
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo bash -c "cat > $NGINX_CONF <<EOF
server {
    listen 80;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_SOCKET;
    }
}
EOF"

    sudo ln -s $NGINX_CONF $NGINX_SYMLINK
    sudo systemctl restart nginx
else
    echo "Nginx reverse proxy configuration already exists."
fi

echo "Stopping any existing Gunicorn process..."
sudo pkill gunicorn || true # '|| true' prevents script from exiting if no gunicorn process is found
sudo rm -f $APP_SOCKET

echo "Starting Gunicorn with the Flask application 🚀"
# Assuming your Flask app instance is named 'app' in 'app.py'
sudo gunicorn --workers 3 --bind unix:$APP_SOCKET 'app:app' --user www-data --group www-data --daemon
echo "Gunicorn started."
