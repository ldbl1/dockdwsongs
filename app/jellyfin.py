import requests

from app.config import settings


def refresh_jellyfin_library() -> bool:
    if not settings.JELLYFIN_URL or not settings.JELLYFIN_API_KEY:
        return False

    url = settings.JELLYFIN_URL.rstrip("/") + "/Library/Refresh"

    headers = {
        "X-Emby-Token": settings.JELLYFIN_API_KEY,
    }

    try:
        response = requests.post(url, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except Exception:
        return False


def jellyfin_configured() -> bool:
    return bool(settings.JELLYFIN_URL and settings.JELLYFIN_API_KEY)