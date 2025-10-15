#!/bin/bash

APP_DIR="/home/ubuntu/app"
SOCK_FILE="$APP_DIR/galeo.sock"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"
GROUP="www-data"

# Navigate to app directory
cd $APP_DIR || exit

echo "📦 Installing Python dependencies"
# Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r requirements.txt

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
    sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled
fi

# Stop any running Gunicorn instances
echo "🛑 Stopping existing Gunicorn processes"
sudo pkill gunicorn || true
sudo rm -f $SOCK_FILE

# Start Gunicorn
echo "🚀 Starting Gunicorn"
$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$SOCK_FILE server:app --daemon

# Ensure socket permissions for Nginx
sudo chown $USER:$GROUP $SOCK_FILE
sudo chmod 660 $SOCK_FILE
sudo chmod 710 $APP_DIR

# Restart Nginx
echo "🔁 Restarting Nginx"
sudo systemctl restart nginx

echo "✅ Deployment complete! Your app should now be live."
