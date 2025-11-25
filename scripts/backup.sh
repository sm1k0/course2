#!/usr/bin/env bash
set -e

DB_NAME="ashan_db"
DB_USER="postgres"         # !!! смотри что в settings.py -> DATABASES['default']['USER']
DB_HOST="localhost"
BACKUP_DIR="./backups"

TIMESTAMP="$(date +'%Y-%m-%d_%H-%M-%S')"

mkdir -p "$BACKUP_DIR"

# ЯВНО указываем pg_dump версии 17
PG_BIN="/opt/homebrew/opt/postgresql@17/bin"

echo "Использую pg_dump из: $PG_BIN"

# Если у БД есть пароль, пропиши его тут один раз:
export PGPASSWORD="1"   # <-- ВПИШИ СВОЙ

echo "Создаю резервную копию БД '$DB_NAME'..."

"$PG_BIN/pg_dump" -h "$DB_HOST" -U "$DB_USER" -F c -b -v \
  -f "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump" "$DB_NAME"

echo "Готово: $BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump"
