#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="picone"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="${SUDO_USER:-${USER}}"

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "Error: user '${APP_USER}' does not exist."
  exit 1
fi

USER_HOME="$(getent passwd "${APP_USER}" | cut -d: -f6)"
if [[ -z "${USER_HOME}" ]]; then
  USER_HOME="/home/${APP_USER}"
fi

MEDIA_MOVIES_DIR="${MEDIA_MOVIES_DIR:-${USER_HOME}/media/movies}"
MEDIA_TV_DIR="${MEDIA_TV_DIR:-${USER_HOME}/media/tv}"
CACHE_DIR="${CACHE_DIR:-${APP_DIR}/data}"

if [[ "${CACHE_DIR}" != /* ]]; then
  CACHE_DIR="${APP_DIR}/${CACHE_DIR#./}"
fi

ENV_FILE="${APP_DIR}/.env"
ENV_TEMPLATE="${APP_DIR}/.env.example"
REQUIREMENTS_FILE="${APP_DIR}/requirements.txt"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -f "${ENV_TEMPLATE}" ]]; then
  echo "Error: ${ENV_TEMPLATE} is missing."
  exit 1
fi

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
  echo "Error: ${REQUIREMENTS_FILE} is missing."
  exit 1
fi

if [[ ${EUID} -eq 0 ]]; then
  SUDO=""
else
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Error: sudo is required when not running as root."
    exit 1
  fi
  SUDO="sudo"
fi

set_env() {
  local key="$1"
  local value="$2"
  local escaped

  escaped="${value//\\/\\\\}"
  escaped="${escaped//&/\\&}"
  escaped="${escaped//|/\\|}"

  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" "${ENV_FILE}"
  else
    printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
  fi
}

echo "[1/7] Installing OS dependencies..."
${SUDO} apt-get update
${SUDO} apt-get install -y python3 python3-venv python3-pip

echo "[2/7] Creating Python virtual environment..."
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  python3 -m venv "${APP_DIR}/.venv"
fi

echo "[3/7] Installing Python requirements..."
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${REQUIREMENTS_FILE}"

echo "[4/7] Preparing environment file..."
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_TEMPLATE}" "${ENV_FILE}"
fi

set_env "MEDIA_MOVIES_DIR" "${MEDIA_MOVIES_DIR}"
set_env "MEDIA_TV_DIR" "${MEDIA_TV_DIR}"
set_env "CACHE_DIR" "${CACHE_DIR}"

echo "[5/7] Creating media and cache directories..."
${SUDO} mkdir -p "${MEDIA_MOVIES_DIR}" "${MEDIA_TV_DIR}" "${CACHE_DIR}"
${SUDO} chown -R "${APP_USER}:${APP_USER}" "${CACHE_DIR}"

echo "[6/7] Installing systemd service..."
${SUDO} tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=PiCone Media Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${APP_DIR}/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "[7/7] Enabling and starting service..."
${SUDO} systemctl daemon-reload
${SUDO} systemctl enable --now "${SERVICE_NAME}"

echo
echo "Installation complete."
echo "Service status:"
${SUDO} systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo
echo "Open PiCone at: http://<pi-ip>:8080"
