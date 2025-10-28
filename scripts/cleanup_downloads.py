#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "dotenv",
#     "qbittorrent-api",
# ]
# ///

import os
from dotenv import load_dotenv
import qbittorrentapi

load_dotenv()

downloads_directory = "/media/storage/arr_data/downloads"


def main() -> None:
    qbt_client = qbittorrentapi.Client(
        host="localhost:8080",
        username=os.getenv("QBIT_USER"),
        password=os.getenv("QBIT_PWD"),
    )

    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(f"Login failed: {e}")

    seeding_torrents = qbt_client.torrents_info(status_filter="seeding")
    all_torrents = qbt_client.torrents_info()
    all_files = os.listdir(downloads_directory)
    all_torrent_files = []

    # Identify directories/files which are not registered as a torrent
    for torrent in all_torrents:
        files = qbt_client.torrents_files(torrent.hash)
        if torrent.state != "metaDL":
            file_or_folder_name = files[0].name.split("/")[0]
            all_torrent_files.append(file_or_folder_name)

    not_torrent_files = list(set(all_files) - set(all_torrent_files))
    for file in not_torrent_files:
        print(f"Not a torrent: {file}")

    # Identify torrents which are seeding but not hardlinked
    for torrent in seeding_torrents:
        files = qbt_client.torrents_files(torrent.hash)
        if len(files) == 1 and files[0].name.count("/") == 0:
            file_name = files[0].name
            stat_info = os.stat(f"{downloads_directory}/{file_name}")
            if stat_info.st_nlink == 1:
                print(f"Not a hard link: {file_name}")
            else:
                print(f"Hard link: {file_name}")
        else:
            folder_name = files[0].name.split("/")[0]
            has_hardlink = False

            for root, dirs, files in os.walk(f"{downloads_directory}/{folder_name}"):
                for file_name in files:
                    full_file_path = os.path.join(root, file_name)
                    stat_info = os.stat(full_file_path)
                    if stat_info.st_nlink > 1:
                        hardlinked_file = file_name
                        has_hardlink = True
                        break

            if not has_hardlink:
                print(f"No hard links: {folder_name}")
            else:
                print(f"Contains a hard link: {hardlinked_file}")


if __name__ == "__main__":
    main()
