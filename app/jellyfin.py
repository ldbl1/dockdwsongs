import requests


def jellyfin_configured(jellyfin_url: str | None, api_key: str | None) -> bool:
    return bool(jellyfin_url and api_key)


def refresh_jellyfin_library(jellyfin_url: str | None, api_key: str | None) -> bool:
    if not jellyfin_configured(jellyfin_url, api_key):
        return False

    url = jellyfin_url.rstrip("/") + "/Library/Refresh"

    headers = {
        "X-Emby-Token": api_key,
    }

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except Exception:
        return False


def test_jellyfin_connection(jellyfin_url: str | None, api_key: str | None) -> bool:
    if not jellyfin_configured(jellyfin_url, api_key):
        return False

    url = jellyfin_url.rstrip("/") + "/System/Info"

    headers = {
        "X-Emby-Token": api_key,
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return True
    except Exception:
        return False