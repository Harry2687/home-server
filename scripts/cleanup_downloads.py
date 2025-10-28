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


def confirm(message: str) -> None:
    confirmation = input(message).strip().lower()
    if confirmation in ("yes", "y"):
        return True
    elif confirmation in ("no", "n"):
        return False
    else:
        print("Invalid input. Please enter 'yes' or 'no'.")


def delete_file_or_dir(path: str) -> None:
    if os.path.isdir(path):
        os.rmdir(path)
    elif os.path.isfile(path):
        os.remove(path)


def delete_file_or_dir_with_confirm(
    path: str, message: str, show_confirm: bool = True
) -> None:
    if show_confirm:
        if confirm(message):
            delete_file_or_dir(path)
    else:
        delete_file_or_dir(path)


def delete_torrent_with_confirm(
    client: qbittorrentapi.Client,
    hash: str,
    message: str,
    downloads_directory: str,
    show_confirm: bool = True,
) -> None:
    file_or_folder_name = client.torrents_files(hash)[0].name.split("/")[0]
    file_or_folder_path = f"{downloads_directory}/{file_or_folder_name}"
    if show_confirm:
        if confirm(message):
            client.torrents_delete(delete_files=False, torrent_hashes=hash)
            delete_file_or_dir(file_or_folder_path)
    else:
        client.torrents_delete(delete_files=False, torrent_hashes=hash)
        delete_file_or_dir(file_or_folder_path)


def main(
    qbt_client: qbittorrentapi.Client,
    downloads_directory: str,
    show_confirm: bool = True,
) -> None:
    try:
        qbt_client.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(f"Login failed: {e}")

    seeding_torrents = qbt_client.torrents_info(status_filter="seeding")
    all_torrents = qbt_client.torrents_info()
    all_files_and_dirs = os.listdir(downloads_directory)
    all_torrent_files_and_dirs = []

    # Identify directories/files which are not registered as a torrent
    for torrent in all_torrents:
        files = qbt_client.torrents_files(torrent.hash)
        if torrent.state != "metaDL":
            file_or_folder_name = files[0].name.split("/")[0]
            all_torrent_files_and_dirs.append(file_or_folder_name)

    not_torrent_files_and_dirs = list(
        set(all_files_and_dirs) - set(all_torrent_files_and_dirs)
    )
    if len(not_torrent_files_and_dirs) > 0:
        for entry in not_torrent_files_and_dirs:
            delete_file_or_dir_with_confirm(
                path=f"{downloads_directory}/{entry}",
                message=f"Not a torrent: {entry} | Delete? (yes/no): ",
                show_confirm=show_confirm,
            )
            print(f"Deleted file/directory (not a torrent): {entry}")
    else:
        print("All files and directories are linked to a torrent.")

    # Identify torrents which are seeding but not hardlinked
    n_torrents_with_no_hardlinks = 0
    for torrent in seeding_torrents:
        files = qbt_client.torrents_files(torrent.hash)
        if len(files) == 1 and files[0].name.count("/") == 0:
            file_name = files[0].name
            stat_info = os.stat(f"{downloads_directory}/{file_name}")
            if stat_info.st_nlink == 1:
                delete_torrent_with_confirm(
                    client=qbt_client,
                    hash=torrent.hash,
                    downloads_directory=downloads_directory,
                    message=f"Not a hard link: {file_name} | Delete? (yes/no): ",
                    show_confirm=show_confirm,
                )
                print(f"Deleted file (not hard linked): {file_name}")
                n_torrents_with_no_hardlinks += 1
        else:
            folder_name = files[0].name.split("/")[0]
            has_hardlink = False

            for root, dirs, files in os.walk(f"{downloads_directory}/{folder_name}"):
                for file_name in files:
                    full_file_path = os.path.join(root, file_name)
                    stat_info = os.stat(full_file_path)
                    if stat_info.st_nlink > 1:
                        has_hardlink = True
                        break

            if not has_hardlink:
                delete_torrent_with_confirm(
                    client=qbt_client,
                    hash=torrent.hash,
                    downloads_directory=downloads_directory,
                    message=f"Does not contain hard links: {folder_name} | Delete? (yes/no): ",
                    show_confirm=show_confirm,
                )
                print(f"Deleted directory (no hard links): {folder_name}")
                n_torrents_with_no_hardlinks += 1

    if n_torrents_with_no_hardlinks == 0:
        print("All torrents contain at least 1 hard link.")


if __name__ == "__main__":
    downloads_directory = "/media/storage/arr_data/downloads"
    qbt_client = qbittorrentapi.Client(
        host="localhost:8080",
        username=os.getenv("QBIT_USER"),
        password=os.getenv("QBIT_PWD"),
    )
    main(qbt_client=qbt_client, downloads_directory=downloads_directory)
