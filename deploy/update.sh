#!/usr/bin/env bash
# Pull the latest code from GitHub and restart the server.
set -euo pipefail
APP_DIR="/opt/vinylaudio"

echo "==> Updating ${APP_DIR}…"
git -C "${APP_DIR}" pull --ff-only
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
systemctl restart storytellers
echo "==> Done. Server restarted."
