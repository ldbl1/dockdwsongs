from pathlib import Path
import re
import unicodedata

from yt_dlp import YoutubeDL

from app.config import settings


INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'


def remove_accents(value: str) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)

    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )


def remove_emojis_and_symbols(value: str) -> str:
    if not value:
        return ""

    cleaned = []

    for char in value:
        category = unicodedata.category(char)

        if category.startswith("So"):
            continue

        cleaned.append(char)

    return "".join(cleaned)


def sanitize_filename(value: str, fallback: str = "youtube_audio") -> str:
    if not value:
        value = fallback

    value = str(value)
    value = remove_accents(value)
    value = remove_emojis_and_symbols(value)

    value = re.sub(INVALID_FILENAME_CHARS, "", value)
    value = value.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .-_")

    if not value:
        value = fallback

    return value


def get_video_info(url: str) -> dict:
    """
    Recupera información del vídeo sin descargarlo.
    """
    options = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "id": info.get("id"),
        "title": info.get("title") or "",
        "uploader": info.get("uploader") or "",
        "channel": info.get("channel") or "",
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail") or "",
        "webpage_url": info.get("webpage_url") or url,
    }


def download_audio(
    url: str,
    audio_format: str = "mp3",
    preferred_title: str | None = None,
) -> Path:
    """
    Descarga audio en /downloads/_incoming.

    El nombre base se limpia para evitar:
    - tildes
    - emojis
    - caracteres inválidos
    - símbolos problemáticos
    """
    settings.INCOMING_PATH.mkdir(parents=True, exist_ok=True)

    info = get_video_info(url)

    raw_title = preferred_title or info.get("title") or info.get("id") or "youtube_audio"
    safe_title = sanitize_filename(raw_title)

    output_template = str(settings.INCOMING_PATH / f"{safe_title}.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "0",
            }
        ],
    }

    with YoutubeDL(options) as ydl:
        downloaded_info = ydl.extract_info(url, download=True)
        prepared_filename = ydl.prepare_filename(downloaded_info)

    return Path(prepared_filename).with_suffix(f".{audio_format}")