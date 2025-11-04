#!/bin/bash
set -e

APP_DIR="/home/ubuntu/Galeo"
SERVICE_NAME="galeo"

echo "🚀 Deploying Galeo App..."

# Ensure app directory exists
if [ ! -d "$APP_DIR" ]; then
  mkdir -p $APP_DIR
fi

# Move project files into place
rsync -av --exclude="venv" --exclude=".git" --exclude=".github" ./ $APP_DIR/

# Move .env if provided
if [ -f ".env" ]; then
  mv .env $APP_DIR/.env
fi

# Install dependencies
echo "📦 Installing dependencies..."
cd $APP_DIR
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Restart Gunicorn service
echo "♻ Restarting Gunicorn..."
sudo systemctl restart $SERVICE_NAME

# Restart Nginx
echo "🔁 Restarting Nginx..."
sudo systemctl restart nginx

echo "✅ Deployment Complete!"
