#!/bin/bash
set -e

APP_DIR="/home/ubuntu/app"
SOCK_FILE="$APP_DIR/galeo.sock"
VENV_DIR="$APP_DIR/venv"
USER="ubuntu"
GROUP="www-data"

echo "🗑️ Cleaning old app files (except venv and .git)"
shopt -s extglob
rm -rf $APP_DIR/!('venv'|'.git'|'deploy.sh')

echo "📦 Moving synced files into app folder"
# Files from rsync already in $APP_DIR, so nothing to move

echo "🔄 Moving env file"
if [ -f "$APP_DIR/env" ]; then
    mv $APP_DIR/env $APP_DIR/.env
fi

echo "⚙️ Installing dependencies"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
$VENV_DIR/bin/pip install --upgrade pip
$VENV/bin/pip install -r $APP_DIR/requirements.txt

echo "🛑 Stopping existing Gunicorn processes"
pkill gunicorn || true
rm -f $SOCK_FILE

echo "🔐 Fixing directory permissions"
chmod 710 /home/ubuntu
chmod 710 $APP_DIR

echo "🚀 Starting Gunicorn"
$VENV_DIR/bin/gunicorn --workers 3 --bind unix:$SOCK_FILE server:app \
    --user $USER --group $GROUP --daemon

echo "🔧 Setting socket permissions"
chown $USER:$GROUP $SOCK_FILE
chmod 660 $SOCK_FILE

echo "🔁 Restarting Nginx"
sudo systemctl restart nginx

echo "✅ Deployment complete! App should be live."
