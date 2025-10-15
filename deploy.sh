#!/bin/bash
set -e

APP_NAME="galeo"
APP_DIR="/home/ubuntu/app"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"

echo "🚀 Starting deployment..."

# --- Install system dependencies ---
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip nginx

# --- Ensure app directory exists ---
cd "$APP_DIR"

# --- Create virtual environment if missing ---
if [ ! -d "venv" ]; then
    echo "🧩 Creating virtual environment..."
    python3 -m venv venv
fi

# --- Activate venv and install requirements ---
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# --- Move env file into place if not renamed ---
if [ -f "env" ]; then
    mv env .env
fi

# --- Create Gunicorn systemd service ---
if [ ! -f "$SERVICE_FILE" ]; then
    echo "🧠 Creating Gunicorn systemd service..."
    sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Gunicorn instance for $APP_NAME
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind unix:$APP_DIR/$APP_NAME.sock server:app

[Install]
WantedBy=multi-user.target
EOF
fi

# --- Enable and restart service ---
echo "♻️ Restarting Gunicorn..."
sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl restart $APP_NAME

# --- Configure Nginx (only once) ---
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
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# --- Restart Nginx ---
echo "🔁 Restarting Nginx..."
sudo systemctl restart nginx

echo "✅ Deployment complete! App is live."
