from pathlib import Path
from typing import Optional

import musicbrainzngs
import requests


musicbrainzngs.set_useragent(
    "dwSongs",
    "1.0",
    "https://github.com/ldbl1/dwSongs",
)


def search_musicbrainz_metadata(artist: str, title: str) -> dict:
    if not artist and not title:
        return {}

    try:
        result = musicbrainzngs.search_recordings(
            artist=artist or "",
            recording=title or "",
            limit=1,
        )

        recordings = result.get("recording-list", [])
        if not recordings:
            return {}

        recording = recordings[0]
        metadata = {
            "title": recording.get("title") or title,
            "artist": artist,
            "album": "",
            "year": "",
            "track_number": "",
            "disc_number": "1",
            "genre": "",
        }

        releases = recording.get("release-list", [])
        if releases:
            release = releases[0]
            metadata["album"] = release.get("title", "")

            date = release.get("date", "")
            if date:
                metadata["year"] = date[:4]

            media_list = release.get("medium-list", [])
            if media_list:
                metadata["disc_number"] = str(media_list[0].get("position", "1"))

                track_list = media_list[0].get("track-list", [])
                if track_list:
                    metadata["track_number"] = str(track_list[0].get("position", ""))

        artist_credit = recording.get("artist-credit", [])
        if artist_credit and isinstance(artist_credit[0], dict):
            artist_obj = artist_credit[0].get("artist", {})
            metadata["artist"] = artist_obj.get("name", artist)

        return metadata
    except Exception:
        return {}


def search_cover_art(artist: str, album: str) -> Optional[str]:
    if not artist or not album:
        return None

    try:
        result = musicbrainzngs.search_releases(
            artist=artist,
            release=album,
            limit=1,
        )

        releases = result.get("release-list", [])
        if not releases:
            return None

        mbid = releases[0]["id"]
        return f"https://coverartarchive.org/release/{mbid}/front"
    except Exception:
        return None


def download_cover(url: str, destination: Path) -> Optional[Path]:
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

        return destination
    except Exception:
        return None