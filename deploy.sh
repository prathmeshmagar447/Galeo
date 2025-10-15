#!/bin/bash
set -e  # Stop on error

APP_NAME="galeo"
APP_DIR="/var/www/$APP_NAME"
ENV_FILE=".env"

echo "🚀 Starting deployment of $APP_NAME"

# --- Cleanup old version ---
if [ -d "$APP_DIR" ]; then
    echo "🧹 Removing old app files..."
    sudo rm -rf "$APP_DIR"
fi

# --- Create app directory ---
echo "📁 Creating app folder..."
sudo mkdir -p "$APP_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR"

# --- Move files to app directory ---
echo "📦 Moving files to app directory..."
sudo cp -r ./* "$APP_DIR"
cd "$APP_DIR"

# --- Rename env file ---
if [ -f "env" ]; then
    mv env .env
fi

# --- Install Python and dependencies ---
echo "🐍 Setting up Python..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip

# --- Create virtual environment ---
echo "🧩 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# --- Setup Nginx ---
if [ ! -f /etc/nginx/sites-available/$APP_NAME ]; then
    echo "⚙️ Configuring Nginx..."
    sudo bash -c "cat > /etc/nginx/sites-available/$APP_NAME" <<EOF
server {
    listen 80;
    server_name _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/$APP_NAME.sock;
    }
}
EOF

    sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
fi

echo "🔁 Restarting Nginx..."
sudo systemctl restart nginx

# --- Restart Gunicorn ---
echo "🔥 Starting Gunicorn..."
sudo pkill gunicorn || true
sudo rm -f $APP_DIR/$APP_NAME.sock

sudo bash -c "cd $APP_DIR && source venv/bin/activate && \
    gunicorn --workers 3 --bind unix:$APP_DIR/$APP_NAME.sock server:app \
    --user www-data --group www-data --daemon"

echo "✅ Deployment complete!"
