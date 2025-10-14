Deployment notes for Galeo / langchain-app

This repository includes a simple `deploy.sh` script that:

- Copies files into `/var/www/langchain-app`
- Creates a Python virtualenv and installs dependencies from `requirements.txt`
- Installs/configures Nginx as a reverse proxy
- Starts Gunicorn bound to a unix socket (`myapp.sock`) as the `www-data` user

Quick steps to run on a Debian/Ubuntu server (as a user with sudo):

1. Copy the repository to the server and change into the project directory.
2. Make the script executable:

```bash
chmod +x deploy.sh
```

3. Run the script (it will use sudo internally):

```bash
./deploy.sh
```

Safety notes and recommendations

- The script will remove the target application folder (`/var/www/langchain-app`) if it exists. Back up any important files before running.
- The script intentionally avoids removing `/var/www` entirely.
- For production use, prefer a systemd service for Gunicorn instead of running it directly via the script. Example service file is shown below.

Example systemd service (`/etc/systemd/system/myapp.service`):

```ini
[Unit]
Description=Gunicorn instance to serve myapp
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/langchain-app
Environment="PATH=/var/www/langchain-app/venv/bin"
ExecStart=/var/www/langchain-app/venv/bin/gunicorn --workers 3 --bind unix:/var/www/langchain-app/myapp.sock app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

After creating the service file, run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable myapp.service
sudo systemctl start myapp.service
```

Logs:
- Gunicorn logs can usually be found via `journalctl -u myapp.service` (if using systemd)
- Nginx logs are at `/var/log/nginx/error.log` and `/var/log/nginx/access.log`

If you want, I can also add the systemd service file creation to the deploy script (safe option) or create a sample `myapp.service` file in the repo. Let me know which you prefer.