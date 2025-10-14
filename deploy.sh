#!/bin/bash
set -euo pipefail

DEPLOY_USER="$1" # Get the EC2_USERNAME passed as an argument
APP_DIR="/var/www/galeo"
NGINX_SITE="/etc/nginx/sites-available/galeo"
SOCKET_NAME="galeo.sock"

echo "Preparing deployment to ${APP_DIR}"

# Safety: only remove the application folder, never /var/www entirely
if [ -d "${APP_DIR}" ]; then
	echo "Removing existing application folder: ${APP_DIR}"
	sudo rm -rf "${APP_DIR}"
fi

echo "Creating application folder"
sudo mkdir -p "${APP_DIR}"

echo "Moving application files to ${APP_DIR}"
# Move all regular files and directories except this deploy script
for item in ./* ./.??*; do
	# skip if glob didn't match
	[ -e "$item" ] || continue
	# skip the deploy script itself
	if [ "$(basename "$item")" = "deploy.sh" ]; then
		continue
	fi
	sudo mv "$item" "${APP_DIR}/" || true
done

echo "Changing ownership of ${APP_DIR} to ${DEPLOY_USER}"
sudo chown -R "${DEPLOY_USER}":"${DEPLOY_USER}" "${APP_DIR}"

# Navigate to the app directory
cd "${APP_DIR}"

# If a virtualenv was named 'env' and should become .env, move it
if [ -d env ] && [ ! -e .env ]; then
	echo "Renaming env -> .env"
	sudo mv env .env
fi

echo "Updating package lists and installing Python if needed"
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

echo "Creating virtualenv and installing dependencies (inside ${APP_DIR})"
if [ ! -d venv ]; then
	python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
	pip install -r requirements.txt
else
	echo "Warning: requirements.txt not found in ${APP_DIR}. Skipping pip install."
fi

# Install Nginx if not present
if ! command -v nginx >/dev/null 2>&1; then
	echo "Installing Nginx"
	sudo apt-get update
	sudo apt-get install -y nginx
fi

# Configure Nginx reverse proxy if not already configured
if [ ! -f "${NGINX_SITE}" ]; then
	echo "Creating Nginx site configuration: ${NGINX_SITE}"
	sudo rm -f /etc/nginx/sites-enabled/default || true
	sudo bash -c "cat > ${NGINX_SITE} <<'EOF'
server {
	listen 80;
	server_name _;

	location / {
		include proxy_params;
		proxy_pass http://unix:${APP_DIR}/${SOCKET_NAME};
	}
}
EOF"

	sudo ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/galeo
	sudo systemctl restart nginx
else
	echo "Nginx reverse proxy configuration already exists: ${NGINX_SITE}"
fi

# Stop any existing Gunicorn process (if any) and remove stale socket
if pgrep -x gunicorn >/dev/null 2>&1; then
	echo "Stopping existing gunicorn processes"
	sudo pkill gunicorn || true
fi
if [ -e "${SOCKET_NAME}" ]; then
	sudo rm -f "${SOCKET_NAME}"
fi

echo "Starting gunicorn"
# Start gunicorn as www-data user, binding to a unix socket inside app dir
sudo -u www-data -H bash -c "source ${APP_DIR}/venv/bin/activate && source ${APP_DIR}/.env && exec gunicorn --workers 3 --bind unix:${APP_DIR}/${SOCKET_NAME} app:app --daemon"

echo "Deployment finished. Verify the service by checking Nginx and Gunicorn logs."
