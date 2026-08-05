#!/bin/bash

# Define variables
START_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RESTIC_PASSWORD="/home/harryzhong/restic_password"
BACKUP_SOURCE="$START_DIR/appdata"
BACKUP_REPO_REMOTE="rclone:gdrive:Backups/optiplexmediaserver"
BACKUP_REPO_LOCAL="/media/storage/backups/appdata"
KEEP_OPTIONS="--keep-daily 7 --keep-weekly 4 --keep-monthly 6"
LOG_FILE="$START_DIR/logs/appdata_backup.log"
MAX_LOG_SIZE=$((5 * 1024 * 1024))

rotate_log() {
  timestamp=$(date +"%Y%m%d_%H%M%S")
  mv "$LOG_FILE" "${LOG_FILE}.${timestamp}"
  echo "[$(date)] Log rotated: ${LOG_FILE}.${timestamp}"
}

if [[ -f "$LOG_FILE" && $(stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]]; then
  rotate_log
fi

echo "[$(date)] Starting Docker AppData backup" >> "$LOG_FILE"

(
  echo "============================================================"
  echo "Docker AppData Backup started (Offline)"
  echo "============================================================"

  cd $START_DIR
  
  # Stop Docker containers
  docker compose down

  # Backup to local repo
  echo "Backing up Docker AppData to local repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose backup $BACKUP_SOURCE

  # Prune local repo
  echo "Pruning local Docker AppData repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Backup to remote repo
  echo "Backing up Docker AppData to remote repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose backup $BACKUP_SOURCE

  # Prune remote repo
  echo "Pruning remote Docker AppData repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Start Docker containers
  docker compose up -d --remove-orphans
  echo "Docker AppData backup complete"

) 2>&1 | ts "%Y-%m-%d %H:%M:%S" | tee -a $LOG_FILE
