#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Storytellers — one-shot installer for an Oracle Cloud "Always Free" Ubuntu VM.
#
# Run it once on a fresh Ubuntu 22.04/24.04 instance:
#
#     curl -fsSL https://raw.githubusercontent.com/andreilucca/vinylaudio/main/deploy/setup.sh | sudo bash
#
# It installs Python + ffmpeg, clones the repo, sets up a gunicorn systemd
# service (auto-starts on boot, restarts on crash) and opens the firewall.
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_URL="https://github.com/andreilucca/vinylaudio.git"
APP_DIR="/opt/vinylaudio"
PORT="8000"
SERVICE="storytellers"

echo "==> Installing system packages (python, ffmpeg, git, nginx)…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg git nginx

echo "==> Cloning / updating the app in ${APP_DIR}…"
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" pull --ff-only
else
  git clone "${REPO_URL}" "${APP_DIR}"
fi

echo "==> Creating Python virtualenv + installing requirements…"
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "==> Installing systemd service (${SERVICE})…"
cat > "/etc/systemd/system/${SERVICE}.service" <<EOF
[Unit]
Description=Storytellers spinning-vinyl video server
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
Environment=PORT=${PORT}
# 3 workers, long timeout so big audio uploads + renders don't get killed.
ExecStart=${APP_DIR}/.venv/bin/gunicorn --workers 3 --timeout 600 --bind 127.0.0.1:${PORT} server:app
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "==> Configuring nginx reverse proxy on port 80…"
cat > "/etc/nginx/sites-available/${SERVICE}" <<'EOF'
server {
    listen 80 default_server;
    server_name _;

    # Allow large audio uploads (e.g. a 6-minute WAV).
    client_max_body_size 200M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}
EOF
ln -sf "/etc/nginx/sites-available/${SERVICE}" "/etc/nginx/sites-enabled/${SERVICE}"
rm -f /etc/nginx/sites-enabled/default

echo "==> Opening the firewall (port 80)…"
# Ubuntu's local firewall (Oracle images ship with iptables rules).
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
# Persist if netfilter-persistent is available.
if command -v netfilter-persistent >/dev/null 2>&1; then
  netfilter-persistent save || true
fi

echo "==> Starting services…"
systemctl daemon-reload
systemctl enable "${SERVICE}"
systemctl restart "${SERVICE}"
nginx -t && systemctl restart nginx

IP="$(curl -fsSL https://api.ipify.org || echo '<your-vm-public-ip>')"
echo ""
echo "============================================================"
echo " Storytellers is live!  →  http://${IP}/"
echo "============================================================"
echo "Update later with:  sudo bash ${APP_DIR}/deploy/update.sh"
