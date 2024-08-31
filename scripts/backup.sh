#!/bin/bash

# Define variables
RESTIC_PASSWORD="/home/harryzhong/restic_password"
BACKUP_SOURCE="/home/harryzhong/docker/appdata"
BACKUP_REPO_REMOTE="rclone:gdrive:Backups/optiplexmediaserver"
BACKUP_REPO_LOCAL="/media/hd1/backups/appdata"
KEEP_OPTIONS="--keep-daily 6 --keep-weekly 3 --keep-monthly 1 --keep-yearly 1"

(
  # Stop Docker containers
  docker compose down

  # Backup to local repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose backup $BACKUP_SOURCE 

  # Prune local repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_LOCAL --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Backup to remote repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose backup $BACKUP_SOURCE 

  # Prune remote repo
  restic -p $RESTIC_PASSWORD -r $BACKUP_REPO_REMOTE --verbose forget $KEEP_OPTIONS --prune --cleanup-cache 

  # Start Docker containers
  docker compose up -d --remove-orphans

) 2>&1 | tee -a /home/harryzhong/docker/logs/$(date +%F_%H-%M-%S)_backup.log
