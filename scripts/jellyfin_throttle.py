# /// script
# dependencies = [
#   "requests",
#   "qbittorrent-api",
# ]
# ///

import ipaddress
import logging
import os
import time

import qbittorrentapi
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://jellyfin:8096")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY")
QBIT_HOST = os.getenv("QBIT_HOST", "http://gluetun:8080")
QBIT_USER = os.getenv("QBIT_USER", "admin")
QBIT_PWD = os.getenv("QBIT_PWD", "adminadmin")
CHECK_INTERVAL = 10  # seconds


def is_remote_ip(ip_str):
    """Checks if an IP address is remote (not local)."""
    try:
        # Jellyfin might return IP:Port
        ip_only = ip_str.split(":")[0]
        ip = ipaddress.ip_address(ip_only)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        logger.warning(f"Could not parse IP address: {ip_str}")
        return True  # Assume remote if we can't parse it?


def get_active_remote_streams():
    """Queries Jellyfin for active remote streams."""
    headers = {"X-Emby-Token": JELLYFIN_API_KEY, "Accept": "application/json"}
    try:
        response = requests.get(f"{JELLYFIN_URL}/Sessions", headers=headers, timeout=10)
        response.raise_for_status()
        sessions = response.json()

        remote_streams = 0
        for session in sessions:
            # Check if something is playing and not paused
            if "NowPlayingItem" in session and not session.get("PlayState", {}).get(
                "IsPaused", True
            ):
                remote_endpoint = session.get("RemoteEndPoint")
                if remote_endpoint and is_remote_ip(remote_endpoint):
                    remote_streams += 1
                    logger.debug(
                        f"Remote stream detected: {session.get('UserName')} on {session.get('Client')} from {remote_endpoint}"
                    )

        return remote_streams
    except Exception as e:
        logger.error(f"Error querying Jellyfin: {e}")
        return -1  # Return -1 to indicate error


def main():
    if not JELLYFIN_API_KEY:
        logger.error("JELLYFIN_API_KEY is not set. Exiting.")
        return

    logger.info("Starting Jellyfin Throttler script...")

    # Initialize qBittorrent client
    qbt_client = qbittorrentapi.Client(
        host=QBIT_HOST, username=QBIT_USER, password=QBIT_PWD
    )

    try:
        qbt_client.auth_log_in()
        logger.info("Connected to qBittorrent.")
    except Exception as e:
        logger.error(f"Failed to connect to qBittorrent: {e}")
        # We'll continue and try to reconnect in the loop if needed

    last_state = None  # None, True (Alt), False (Global)

    while True:
        remote_streams = get_active_remote_streams()

        if remote_streams != -1:
            should_throttle = remote_streams > 0

            if should_throttle != last_state:
                try:
                    # Refresh auth if needed
                    if not qbt_client.is_logged_in:
                        qbt_client.auth_log_in()

                    if should_throttle:
                        logger.info(
                            f"Active remote streams: {remote_streams}. Activating alternative rate limits."
                        )
                        qbt_client.transfer_set_speed_limits_mode(True)
                    else:
                        logger.info(
                            "No active remote streams. Activating global rate limits."
                        )
                        qbt_client.transfer_set_speed_limits_mode(False)

                    last_state = should_throttle
                except Exception as e:
                    logger.error(f"Error updating qBittorrent speed limits: {e}")
                    last_state = None  # Reset state to retry next time

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
