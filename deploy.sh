#!/bin/bash
set -e

# Navigate to the project directory
cd /home/ubuntu/Galeo

# Pull the latest changes from the main branch
git pull origin main

# Create or update the .env file
echo "${{ secrets.ENV }}" > .env

# Activate the virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Restart the application (example using pkill and nohup)
# You might need to adjust this depending on how you run your app
pkill -f "python app.py" || true
nohup python app.py &