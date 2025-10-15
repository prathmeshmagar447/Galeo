#!/bin/bash
set -e

APP_DIR="/home/ubuntu/app"
SERVICE_NAME="galeo" # Your Gunicorn systemd service name

echo "Navigating to application directory: $APP_DIR"
cd $APP_DIR

echo "Pulling latest code from main branch..."
git pull origin main

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Copying .env file..."
# Assuming the .env file is transferred to $APP_DIR/env by GitHub Actions
cp env .env

echo "Restarting Gunicorn service: $SERVICE_NAME"
sudo systemctl restart $SERVICE_NAME

echo "Reloading Nginx..."
sudo systemctl reload nginx

echo "Deployment complete!"
