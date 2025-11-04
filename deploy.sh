#!/bin/bash
set -e

APP_DIR="/home/ubuntu/Galeo"
SERVICE_NAME="galeo"

echo "🚀 Starting deployment..."

# Ensure target directory exists
mkdir -p $APP_DIR

echo "📦 Syncing updated code (keeping venv)..."
sudo rsync -av --delete --exclude="venv" --exclude=".git" ./ $APP_DIR/

# Fix permissions for .env if present
if [ -f "$APP_DIR/.env" ]; then
  echo "🔐 Setting .env permissions..."
  sudo chmod 600 $APP_DIR/.env
fi

echo "🐍 Ensuring virtual environment exists..."
if [ ! -d "$APP_DIR/venv" ]; then
  echo "⚙️ Creating venv..."
  python3 -m venv $APP_DIR/venv
fi

echo "📦 Installing dependencies..."
source $APP_DIR/venv/bin/activate
pip install --upgrade pip
pip install -r $APP_DIR/requirements.txt
deactivate

echo "♻ Restarting Gunicorn..."
sudo systemctl restart $SERVICE_NAME

echo "🔁 Restarting Nginx..."
sudo systemctl restart nginx

echo "✅ Deployment Finished Successfully!"
