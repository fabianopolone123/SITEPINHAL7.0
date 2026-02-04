#!/usr/bin/env bash
set -euo pipefail

# Deploy simples via git pull + migrate + collectstatic + restart.
# Ajuste os caminhos conforme seu servidor.

APP_DIR="/srv/sitepinhal/current"
VENV="/srv/sitepinhal/venv"

cd "$APP_DIR"

echo "[1/5] Atualizando codigo..."
git pull --ff-only

echo "[2/5] Instalando deps..."
"$VENV/bin/pip" install -r backend/requirements.txt

echo "[3/5] Migrando banco..."
"$VENV/bin/python" backend/manage.py migrate --noinput

echo "[4/5] Coletando arquivos estaticos..."
"$VENV/bin/python" backend/manage.py collectstatic --noinput

echo "[5/5] Reiniciando servicos..."
systemctl restart sitepinhal
systemctl reload nginx

echo "Deploy concluido."
