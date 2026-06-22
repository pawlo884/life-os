#!/bin/sh
set -e

BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="lifeos_${TIMESTAMP}.sql"

pg_dump -U lifeos -d lifeos -f "${BACKUP_DIR}/${FILENAME}"
echo "Backup saved: ${BACKUP_DIR}/${FILENAME}"
