from pathlib import Path
import re
import shutil

from app.config import settings


def sanitize(value: str) -> str:
    value = value or "Unknown"
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = value.strip()
    return value or "Unknown"


def unique_path(path: Path) -> tuple[Path, bool]:
    if not path.exists():
        return path, False

    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate, True
        counter += 1


def organize_audio(
    file_path: Path,
    metadata: dict,
    cover_path: Path | None = None,
) -> tuple[Path, bool]:
    artist = sanitize(metadata.get("artist", "Unknown Artist"))
    album = sanitize(metadata.get("album", "Unknown Album"))
    year = sanitize(metadata.get("year", "Unknown Year"))
    title = sanitize(metadata.get("title", file_path.stem))

    track_raw = metadata.get("track_number") or "1"
    track = sanitize(track_raw).zfill(2)

    destination_dir = settings.DOWNLOAD_PATH / "Music" / artist / f"{album} ({year})"
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / f"{track} - {title}{file_path.suffix}"
    destination, duplicate = unique_path(destination)

    shutil.move(str(file_path), destination)

    if cover_path and cover_path.exists():
        shutil.copyfile(cover_path, destination_dir / "cover.jpg")
        shutil.copyfile(cover_path, destination_dir / "folder.jpg")

    return destination, duplicate