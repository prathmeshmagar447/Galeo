#!/bin/bash
set -e

APP_DIR="/home/ubuntu/Galeo"
SERVICE_NAME="galeo"

echo "🚀 Starting deployment..."

# Ensure target directory exists
mkdir -p $APP_DIR

echo "📦 Syncing updated code..."
sudo rsync -av --delete --exclude="venv" --exclude=".git" ./ $APP_DIR/

# Ensure .env permissions are correct (do NOT move)
if [ -f "$APP_DIR/.env" ]; then
  echo "🔐 Setting .env permissions..."
  sudo chmod 600 $APP_DIR/.env
fi

echo "🐍 Installing dependencies..."
cd $APP_DIR
source venv/bin/activate
pip install -r requirements.txt
deactivate

echo "♻ Restarting Gunicorn..."
sudo systemctl restart $SERVICE_NAME

echo "🔁 Restarting Nginx..."
sudo systemctl restart nginx

echo "✅ Deployment Finished Successfully!"
