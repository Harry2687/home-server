#!/bin/bash

# Define variables
START_DIR="/home/harryzhong/home-server"
RESTIC_PASSWORD="/home/harryzhong/restic_password"
BACKUP_SOURCE="$START_DIR/appdata"
BACKUP_REPO_REMOTE="rclone:gdrive:Backups/optiplexmediaserver"
BACKUP_REPO_LOCAL="/media/storage/backups/appdata"
KEEP_OPTIONS="--keep-daily 3 --keep-weekly 2 --keep-monthly 1"
LOG_FILE="$START_DIR/logs/restic_backup.log"
MAX_LOG_SIZE=$((5 * 1024 * 1024))

rotate_log() {
  timestamp=$(date +"%Y%m%d_%H%M%S")
  mv "$LOG_FILE" "${LOG_FILE}.${timestamp}"
  echo "[$(date)] Log rotated: ${LOG_FILE}.${timestamp}"
}

if [[ -f "$LOG_FILE" && $(stat -c%s "$LOG_FILE") -gt $MAX_SIZE ]]; then
  rotate_log
fi

echo "[$(date)] This is a log message" >> "$LOG_FILE"

(
  echo "============================================================"
  echo "Backup started"
  echo "============================================================"

  cd $START_DIR
  
  # Stop Docker containers
  docker compose down

  # Backup to local repo
  echo "Backing up to local repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose backup $BACKUP_SOURCE

  # Prune local repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Backup to remote repo
  echo "Backing up to remote repo..."
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose backup $BACKUP_SOURCE

  # Prune remote repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Start Docker containers
  docker compose up -d --remove-orphans
  echo "Backup complete"

) 2>&1 | ts "%Y-%m-%d %H:%M:%S" | tee -a $LOG_FILE
