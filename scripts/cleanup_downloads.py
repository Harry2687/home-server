#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "apscheduler",
#     "dotenv",
#     "qbittorrent-api",
# ]
# ///

import os
import shutil
import logging
from dotenv import load_dotenv
import qbittorrentapi
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env if it exists
load_dotenv()


def delete_file_or_dir(path: str) -> None:
    """Deletes a file or directory at the given path."""
    if os.path.isdir(path):
        try:
            shutil.rmtree(path)
            logger.info(f"Deleted directory: {path}")
        except Exception as e:
            logger.error(f"Failed to delete directory {path}: {e}")
    elif os.path.isfile(path):
        try:
            os.remove(path)
            logger.info(f"Deleted file: {path}")
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")


def delete_torrent(
    client: qbittorrentapi.Client,
    torrent_hash: str,
    downloads_directory: str,
) -> None:
    """Deletes a torrent from qBittorrent and its associated files from disk."""
    try:
        files = client.torrents_files(torrent_hash)
        if not files:
            logger.warning(f"No files found for torrent {torrent_hash}")
            return

        file_or_folder_name = files[0].name.split("/")[0]
        file_or_folder_path = os.path.join(downloads_directory, file_or_folder_name)

        # Delete from qBittorrent without deleting files (we'll delete them manually to ensure they are gone)
        client.torrents_delete(delete_files=False, torrent_hashes=torrent_hash)
        delete_file_or_dir(file_or_folder_path)
    except Exception as e:
        logger.error(f"Error deleting torrent {torrent_hash}: {e}")


def run_cleanup():
    """Main cleanup logic to identify and remove unneeded files and torrents."""
    logger.info("Starting cleanup job...")

    qbt_host = os.getenv("QBIT_HOST", "http://localhost:8080")
    qbt_user = os.getenv("QBIT_USER")
    qbt_pwd = os.getenv("QBIT_PWD")
    mediadir = os.getenv("MEDIADIR")

    if not mediadir:
        logger.error("MEDIADIR environment variable not set.")
        return

    downloads_directory = os.path.join(mediadir, "downloads")

    qbt_client = qbittorrentapi.Client(
        host=qbt_host,
        username=qbt_user,
        password=qbt_pwd,
    )

    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        logger.error(f"qBittorrent login failed: {e}")
        return
    except Exception as e:
        logger.error(f"Could not connect to qBittorrent at {qbt_host}: {e}")
        return

    try:
        seeding_torrents = qbt_client.torrents_info(status_filter="seeding")
        all_torrents = qbt_client.torrents_info()
    except Exception as e:
        logger.error(f"Error fetching torrent info: {e}")
        return

    if not os.path.exists(downloads_directory):
        logger.error(f"Downloads directory not found: {downloads_directory}")
        return

    all_files_and_dirs = os.listdir(downloads_directory)
    all_torrent_files_and_dirs = []

    # Identify directories/files which are registered as a torrent
    for torrent in all_torrents:
        try:
            files = qbt_client.torrents_files(torrent.hash)
            if torrent.state != "metaDL" and files:
                file_or_folder_name = files[0].name.split("/")[0]
                all_torrent_files_and_dirs.append(file_or_folder_name)
        except Exception as e:
            logger.error(f"Error getting files for torrent {torrent.hash}: {e}")

    # Remove files/dirs not associated with any torrent
    not_torrent_files_and_dirs = list(
        set(all_files_and_dirs) - set(all_torrent_files_and_dirs)
    )

    if not_torrent_files_and_dirs:
        for entry in not_torrent_files_and_dirs:
            path = os.path.join(downloads_directory, entry)
            logger.info(f"Not associated with any torrent: {entry}")
            delete_file_or_dir(path)
    else:
        logger.info("All files and directories in downloads are linked to a torrent.")

    # Identify torrents which are seeding but not hardlinked
    n_torrents_deleted = 0
    for torrent in seeding_torrents:
        try:
            files = qbt_client.torrents_files(torrent.hash)
            if not files:
                continue

            # Single file torrent
            if len(files) == 1 and files[0].name.count("/") == 0:
                file_name = files[0].name
                file_path = os.path.join(downloads_directory, file_name)
                if os.path.exists(file_path):
                    stat_info = os.stat(file_path)
                    if stat_info.st_nlink == 1:
                        logger.info(f"Seeding with no hardlinks (file): {file_name}")
                        delete_torrent(qbt_client, torrent.hash, downloads_directory)
                        n_torrents_deleted += 1
            # Multi-file/folder torrent
            else:
                folder_name = files[0].name.split("/")[0]
                folder_path = os.path.join(downloads_directory, folder_name)

                if os.path.exists(folder_path):
                    has_hardlink = False
                    for root, _, walk_files in os.walk(folder_path):
                        for file_name in walk_files:
                            full_file_path = os.path.join(root, file_name)
                            stat_info = os.stat(full_file_path)
                            if stat_info.st_nlink > 1:
                                has_hardlink = True
                                break
                        if has_hardlink:
                            break

                    if not has_hardlink:
                        logger.info(
                            f"Seeding with no hardlinks (folder): {folder_name}"
                        )
                        delete_torrent(qbt_client, torrent.hash, downloads_directory)
                        n_torrents_deleted += 1
        except Exception as e:
            logger.error(f"Error processing torrent {torrent.hash}: {e}")

    if n_torrents_deleted == 0:
        logger.info("All seeding torrents contain at least one hard link.")
    else:
        logger.info(
            f"Cleanup finished. Deleted {n_torrents_deleted} seeding torrent(s)."
        )


if __name__ == "__main__":
    cron_schedule = os.getenv("CRON_SCHEDULE")

    if cron_schedule:
        logger.info(f"Cron schedule detected: {cron_schedule}")
        scheduler = BlockingScheduler()
        try:
            scheduler.add_job(run_cleanup, CronTrigger.from_crontab(cron_schedule))
            # Run once immediately on startup
            run_cleanup()
            logger.info("Scheduler started. Press Ctrl+C to exit.")
            scheduler.start()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            # Fallback to single run if scheduler fails
            run_cleanup()
    else:
        logger.info("No CRON_SCHEDULE found, running once.")
        run_cleanup()
