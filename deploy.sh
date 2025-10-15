#!/bin/bash
set -e

APP_DIR="/home/ubuntu/app"
SOCK_FILE="$APP_DIR/galeo.sock"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"
GROUP="www-data"

echo "📂 Navigating to app directory"
cd $APP_DIR || exit

# Ensure virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "🛠️ Creating Python virtual environment"
    python3 -m venv $VENV_DIR
fi

echo "📦 Installing Python dependencies"
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r requirements.txt

# Stop any existing Gunicorn processes
echo "🛑 Stopping existing Gunicorn processes"
sudo pkill gunicorn || true
sudo rm -f $SOCK_FILE

# Start Gunicorn
echo "🚀 Starting Gunicorn"
$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$SOCK_FILE server:app --daemon

# Fix socket permissions so Nginx can access
sudo chown $USER:$GROUP $SOCK_FILE
sudo chmod 660 $SOCK_FILE
sudo chmod 710 $APP_DIR

# Configure Nginx if not already configured
NGINX_CONF="/etc/nginx/sites-available/galeo"
if [ ! -f $NGINX_CONF ]; then
    echo "🛠️ Configuring Nginx"
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

# Restart Nginx
echo "🔁 Restarting Nginx"
sudo systemctl restart nginx

echo "✅ Deployment complete!"
