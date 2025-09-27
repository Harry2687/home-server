#!/bin/bash

# Define variables
DOCKERDIR="/home/harryzhong/docker"
RESTIC_PASSWORD="/home/harryzhong/restic_password"
BACKUP_SOURCE="/home/harryzhong/docker/appdata"
BACKUP_REPO_REMOTE="rclone:gdrive:Backups/optiplexmediaserver"
BACKUP_REPO_LOCAL="/media/hd1/backups/appdata"
KEEP_OPTIONS="--keep-daily 3 --keep-weekly 2 --keep-monthly 1"

(
  cd $DOCKERDIR
  
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
