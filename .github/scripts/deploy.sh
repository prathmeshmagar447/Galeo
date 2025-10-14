#!/bin/bash
set -e

echo "Deploying application to EC2..."

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv

# Navigate to the application directory (assuming it's in /home/ubuntu/Galeo)
# You might need to adjust this path based on where your application resides on the EC2 instance
cd /home/ubuntu/Galeo

# Pull the latest code
git pull origin main

# Install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restart the application using Gunicorn managed by systemd
# This assumes you have a systemd service file set up for your Gunicorn application.
# Example systemd service file (e.g., /etc/systemd/system/galeo.service):
# [Unit]
# Description=Gunicorn instance to serve Galeo
# After=network.target
#
# [Service]
# User=ubuntu
# Group=www-data
# WorkingDirectory=/home/ubuntu/Galeo
# Environment="PATH=/home/ubuntu/Galeo/venv/bin"
# ExecStart=/home/ubuntu/Galeo/venv/bin/gunicorn --workers 3 --bind unix:galeo.sock -m 007 wsgi:app
# Restart=always
#
# [Install]
# WantedBy=multi-user.target
#
# Create/Update the systemd service file for Gunicorn
sudo tee /etc/systemd/system/galeo.service > /dev/null <<EOF
[Unit]
Description=Gunicorn instance to serve Galeo
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/Galeo
Environment="PATH=/home/ubuntu/Galeo/venv/bin"
ExecStart=/home/ubuntu/Galeo/venv/bin/gunicorn --workers 3 --bind unix:galeo.sock -m 007 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable, and restart the service
sudo systemctl daemon-reload
sudo systemctl enable galeo.service
sudo systemctl restart galeo.service

echo "Deployment complete!"
