# My Server

Docker Compose files for my Ubuntu home server.

## How to restore appdata

This is specific to my backup strategy.

1. Install `restic` and `rclone`.
2. Set up Google Drive `rclone` remote named gdrive.
3. Run the command below.

```bash
restic -r rclone:gdrive:/Backups/optiplexmediaserver restore latest:/home/harryzhong/docker/appdata --target ./appdata
```