#!/usr/bin/env bash
set -e

DB_NAME="ashan_db"
DB_USER="postgres"         # тот же юзер, что и в backup.sh и settings.py
DB_HOST="localhost"

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Использование: $0 path/to/backup.dump"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Файл бэкапа не найден: $BACKUP_FILE"
  exit 1
fi

PG_BIN="/opt/homebrew/opt/postgresql@17/bin"

echo "Использую pg инструменты из: $PG_BIN"

# пароль к БД
export PGPASSWORD="1"   # тот же пароль

echo "Восстанавливаю БД '$DB_NAME' из бэкапа '$BACKUP_FILE'..."

"$PG_BIN/dropdb" -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" || true
"$PG_BIN/createdb" -h "$DB_HOST" -U "$DB_USER" "$DB_NAME"

"$PG_BIN/pg_restore" -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v "$BACKUP_FILE"

echo "Восстановление завершено."
