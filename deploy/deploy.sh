#!/usr/bin/env bash
set -Eeuo pipefail
umask 027

# Deploy completo para VPS:
# - puxa a ultima versao do git
# - instala dependencias
# - roda check/migrate/collectstatic
# - reinicia servicos
# - valida healthcheck
# - rollback automatico em caso de falha

APP_DIR="${APP_DIR:-/srv/sitepinhal/current}"
VENV_DIR="${VENV_DIR:-/srv/sitepinhal/venv}"
ENV_FILE="${ENV_FILE:-/etc/sitepinhal.env}"
SERVICE_NAME="${SERVICE_NAME:-sitepinhal}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"
REMOTE_NAME="${REMOTE_NAME:-origin}"
BRANCH_NAME="${BRANCH_NAME:-main}"
BACKUP_DIR="${BACKUP_DIR:-/srv/sitepinhal/backup}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://127.0.0.1:8000/login/}"
LOCK_FILE="${LOCK_FILE:-/tmp/sitepinhal_deploy.lock}"
KEEP_BACKUPS="${KEEP_BACKUPS:-15}"

PIP_BIN="$VENV_DIR/bin/pip"
PYTHON_BIN="$VENV_DIR/bin/python"
MANAGE_PY="$APP_DIR/backend/manage.py"

ROLLBACK_READY=0
PREVIOUS_COMMIT=""
DB_PATH=""
DB_BACKUP=""

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
  log "ERRO: $*"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Comando obrigatorio nao encontrado: $1"
}

rollback() {
  local exit_code=$?
  if [[ "$ROLLBACK_READY" -ne 1 ]]; then
    exit "$exit_code"
  fi

  log "Falha detectada. Iniciando rollback..."
  set +e

  if [[ -n "$PREVIOUS_COMMIT" ]]; then
    log "Voltando codigo para commit anterior: $PREVIOUS_COMMIT"
    git -C "$APP_DIR" reset --hard "$PREVIOUS_COMMIT" >/dev/null 2>&1
  fi

  if [[ -n "$DB_PATH" && -n "$DB_BACKUP" && -f "$DB_BACKUP" ]]; then
    log "Restaurando banco SQLite do backup..."
    cp -f "$DB_BACKUP" "$DB_PATH"
  fi

  log "Reiniciando servico da aplicacao apos rollback..."
  systemctl restart "$SERVICE_NAME" >/dev/null 2>&1
  systemctl reload "$NGINX_SERVICE" >/dev/null 2>&1

  if curl -fsS --max-time 10 "$HEALTHCHECK_URL" >/dev/null 2>&1; then
    log "Rollback concluido e aplicacao voltou a responder."
  else
    log "Rollback executado, mas healthcheck ainda falhou. Verifique os logs."
  fi
  exit "$exit_code"
}

trap rollback ERR

# Lock para evitar 2 deploys ao mesmo tempo.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  die "Ja existe um deploy em andamento (lock: $LOCK_FILE)"
fi

require_cmd git
require_cmd curl
require_cmd systemctl
require_cmd flock

[[ -d "$APP_DIR/.git" ]] || die "Repositorio git nao encontrado em $APP_DIR"
[[ -x "$PIP_BIN" ]] || die "pip nao encontrado em $PIP_BIN"
[[ -x "$PYTHON_BIN" ]] || die "python nao encontrado em $PYTHON_BIN"
[[ -f "$MANAGE_PY" ]] || die "manage.py nao encontrado em $MANAGE_PY"
[[ -f "$ENV_FILE" ]] || die "Arquivo de ambiente nao encontrado em $ENV_FILE"

mkdir -p "$BACKUP_DIR"

log "Carregando variaveis de ambiente..."
set -a
source "$ENV_FILE"
set +a

if [[ -z "${DJANGO_SECRET_KEY:-}" ]]; then
  die "DJANGO_SECRET_KEY nao definido em $ENV_FILE"
fi

PREVIOUS_COMMIT="$(git -C "$APP_DIR" rev-parse HEAD)"
ROLLBACK_READY=1

DB_PATH="${DJANGO_SQLITE_PATH:-}"
if [[ -n "$DB_PATH" && -f "$DB_PATH" ]]; then
  timestamp="$(date +%Y%m%d_%H%M%S)"
  DB_BACKUP="$BACKUP_DIR/db_before_deploy_${timestamp}.sqlite3"
  log "Criando backup do banco SQLite em $DB_BACKUP"
  cp -f "$DB_PATH" "$DB_BACKUP"
fi

log "Atualizando codigo para a ultima versao ($REMOTE_NAME/$BRANCH_NAME)..."
git -C "$APP_DIR" fetch --prune "$REMOTE_NAME"
TARGET_COMMIT="$(git -C "$APP_DIR" rev-parse "$REMOTE_NAME/$BRANCH_NAME")"
git -C "$APP_DIR" reset --hard "$TARGET_COMMIT"

log "Instalando/atualizando dependencias..."
"$PIP_BIN" install -r "$APP_DIR/backend/requirements.txt"

log "Validando configuracao Django..."
"$PYTHON_BIN" "$MANAGE_PY" check

log "Aplicando migracoes..."
"$PYTHON_BIN" "$MANAGE_PY" migrate --noinput

log "Coletando arquivos estaticos..."
"$PYTHON_BIN" "$MANAGE_PY" collectstatic --noinput

log "Reiniciando servicos..."
systemctl restart "$SERVICE_NAME"
systemctl reload "$NGINX_SERVICE"

log "Aguardando aplicacao subir..."
sleep 2

log "Executando healthcheck em $HEALTHCHECK_URL"
for attempt in 1 2 3 4 5; do
  if curl -fsS --max-time 10 "$HEALTHCHECK_URL" >/dev/null 2>&1; then
    log "Healthcheck OK."
    break
  fi
  if [[ "$attempt" -eq 5 ]]; then
    die "Healthcheck falhou apos 5 tentativas."
  fi
  sleep 2
done

if [[ "$KEEP_BACKUPS" =~ ^[0-9]+$ ]]; then
  log "Limpando backups antigos (mantendo os $KEEP_BACKUPS mais recentes)..."
  mapfile -t old_backups < <(ls -1t "$BACKUP_DIR"/db_before_deploy_*.sqlite3 2>/dev/null | tail -n +"$((KEEP_BACKUPS + 1))")
  if [[ "${#old_backups[@]}" -gt 0 ]]; then
    rm -f "${old_backups[@]}"
  fi
fi

ROLLBACK_READY=0
log "Deploy concluido com sucesso."
log "Commit anterior: $PREVIOUS_COMMIT"
log "Commit atual:    $TARGET_COMMIT"
