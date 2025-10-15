#!/bin/bash

APP_DIR="/home/ubuntu/app"
SOCK_FILE="$APP_DIR/galeo.sock"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"
GROUP="www-data"

echo "🗑️  Deleting old app files"
sudo rm -rf $APP_DIR/*

echo "📁 Creating app folder"
sudo mkdir -p $APP_DIR

echo "🚚 Moving files to app folder"
sudo mv * $APP_DIR

# Navigate to app directory
cd $APP_DIR

echo "🔄 Moving env file"
sudo mv env .env

echo "⚙️  Updating system and installing dependencies"
sudo apt-get update
sudo apt-get install -y python3 python3-pip nginx

# Install python packages
echo "📦 Installing Python dependencies"
sudo $VENV_DIR/bin/pip install -r requirements.txt

# Configure Nginx reverse proxy
NGINX_CONF="/etc/nginx/sites-available/galeo"
if [ ! -f $NGINX_CONF ]; then
    echo "🛠️  Configuring Nginx"
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo bash -c "cat > $NGINX_CONF <<EOF
server {
    listen 80;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$SOCK_FILE;
    }
}
EOF"
    sudo ln -s $NGINX_CONF /etc/nginx/sites-enabled
fi

# Fix directory permissions for Nginx to access the socket
echo "🔐 Fixing directory permissions"
sudo chmod 710 /home/ubuntu
sudo chmod 710 $APP_DIR

# Stop any running Gunicorn instances
echo "🛑 Stopping existing Gunicorn processes"
sudo pkill gunicorn || true
sudo rm -f $SOCK_FILE

# Start Gunicorn
echo "🚀 Starting Gunicorn"
sudo $VENV_DIR/bin/gunicorn --workers 3 --bind unix:$SOCK_FILE server:app \
     --user $USER --group $GROUP --daemon

# Ensure socket permissions
sudo chown $USER:$GROUP $SOCK_FILE
sudo chmod 660 $SOCK_FILE

# Restart Nginx
echo "🔁 Restarting Nginx"
sudo systemctl restart nginx

echo "✅ Deployment complete! Your app should now be live."
