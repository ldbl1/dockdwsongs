from pathlib import Path

from yt_dlp import YoutubeDL

from app.config import settings


def get_video_info(url: str) -> dict:
    options = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with YoutubeDL(options) as ydl:
        return ydl.extract_info(url, download=False)


def download_audio(url: str, audio_format: str = "mp3") -> Path:
    temp_dir = settings.DOWNLOAD_PATH / "_incoming"
    temp_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(temp_dir / "%(title)s.%(ext)s")

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
        info = ydl.extract_info(url, download=True)
        prepared = ydl.prepare_filename(info)

    return Path(prepared).with_suffix(f".{audio_format}")