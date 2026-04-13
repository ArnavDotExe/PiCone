#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="picone"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="${SUDO_USER:-${USER}}"
SKIP_APT="${SKIP_APT:-0}"

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

check_runtime_deps() {
  local missing=()

  if ! command -v python3 >/dev/null 2>&1; then
    missing+=("python3" "python3-venv")
  else
    if ! python3 -m venv --help >/dev/null 2>&1; then
      missing+=("python3-venv")
    fi
  fi

  printf '%s\n' "${missing[@]}"
}

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

echo "[1/7] Checking OS dependencies..."
mapfile -t MISSING_DEPS < <(check_runtime_deps)

if [[ ${#MISSING_DEPS[@]} -eq 0 ]]; then
  echo "OS dependencies already installed."
else
  if [[ "${SKIP_APT}" == "1" ]]; then
    echo "Error: missing OS packages: ${MISSING_DEPS[*]}"
    echo "SKIP_APT=1 is set, so apt installation is disabled."
    exit 1
  fi

  echo "Installing missing OS packages: ${MISSING_DEPS[*]}"
  if ! ${SUDO} apt-get update; then
    echo ""
    echo "apt-get update failed."
    echo "Your system likely has repository key or source issues."
    echo "If Python is already installed, rerun with: SKIP_APT=1 ./install.sh"
    exit 1
  fi

  ${SUDO} apt-get install -y "${MISSING_DEPS[@]}"
fi

echo "[2/7] Creating Python virtual environment..."
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  python3 -m venv "${APP_DIR}/.venv"
fi

echo "[3/7] Installing Python requirements..."
if ! "${APP_DIR}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
  "${APP_DIR}/.venv/bin/python" -m ensurepip --upgrade
fi

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
