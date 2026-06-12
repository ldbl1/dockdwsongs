from pathlib import Path
from typing import Optional

import musicbrainzngs
import requests


musicbrainzngs.set_useragent(
    "dwSongs",
    "1.0",
    "https://github.com/ldbl1/dockdwsongs",
)


def _safe_str(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _first_tag_name(entity: dict) -> str:
    """
    Intenta extraer género/tag desde MusicBrainz.

    MusicBrainz puede devolver:
    - tag-list
    - genre-list

    No siempre está disponible.
    """
    genre_list = entity.get("genre-list", []) or []
    if genre_list:
        name = genre_list[0].get("name")
        if name:
            return _safe_str(name)

    tag_list = entity.get("tag-list", []) or []
    if tag_list:
        name = tag_list[0].get("name")
        if name:
            return _safe_str(name)

    return ""


def _artist_from_credit(recording: dict, fallback: str = "") -> str:
    artist_credit = recording.get("artist-credit", []) or []

    if not artist_credit:
        return fallback

    names = []

    for credit in artist_credit:
        if isinstance(credit, dict):
            artist_obj = credit.get("artist", {})
            name = artist_obj.get("name")
            if name:
                names.append(name)
        elif isinstance(credit, str):
            # MusicBrainz a veces mete separadores como " feat. "
            if credit.strip():
                names.append(credit.strip())

    joined = "".join(names).strip()

    return joined or fallback


def _extract_release_metadata(recording: dict) -> dict:
    """
    Extrae álbum, año, número de disco y pista desde el primer release
    que tenga información suficiente.
    """
    releases = recording.get("release-list", []) or []

    best = {
        "album": "",
        "year": "",
        "track_number": "",
        "disc_number": "1",
        "release_mbid": "",
        "genre": "",
    }

    if not releases:
        return best

    for release in releases:
        album = _safe_str(release.get("title"))
        release_mbid = _safe_str(release.get("id"))

        date = _safe_str(release.get("date"))
        year = date[:4] if date else ""

        release_genre = _first_tag_name(release)

        medium_list = release.get("medium-list", []) or []

        if not medium_list:
            # Aun sin pistas, si trae álbum/año ya es útil.
            if album or year:
                best.update(
                    {
                        "album": album,
                        "year": year,
                        "release_mbid": release_mbid,
                        "genre": release_genre,
                    }
                )
                return best

            continue

        for medium in medium_list:
            disc_number = _safe_str(medium.get("position")) or "1"
            track_list = medium.get("track-list", []) or []

            if not track_list:
                continue

            for track in track_list:
                track_number = _safe_str(track.get("position"))

                # En algunos resultados, track["recording"]["id"] coincide con recording["id"].
                track_recording = track.get("recording", {}) or {}
                track_recording_id = _safe_str(track_recording.get("id"))
                recording_id = _safe_str(recording.get("id"))

                if recording_id and track_recording_id and recording_id != track_recording_id:
                    continue

                best.update(
                    {
                        "album": album,
                        "year": year,
                        "track_number": track_number,
                        "disc_number": disc_number,
                        "release_mbid": release_mbid,
                        "genre": release_genre or _first_tag_name(track_recording),
                    }
                )

                return best

        # Fallback si medium existe pero no hemos encontrado match exacto.
        if album or year:
            best.update(
                {
                    "album": album,
                    "year": year,
                    "release_mbid": release_mbid,
                    "genre": release_genre,
                }
            )
            return best

    return best


def search_musicbrainz_metadata(artist: str, title: str) -> dict:
    """
    Busca metadatos de una canción en MusicBrainz.

    Devuelve un dict con:
    - title
    - artist
    - album_artist
    - album
    - year
    - track_number
    - disc_number
    - genre
    - release_mbid
    """
    artist = _safe_str(artist)
    title = _safe_str(title)

    if not artist and not title:
        return {}

    try:
        result = musicbrainzngs.search_recordings(
            artist=artist,
            recording=title,
            limit=5,
        )

        recordings = result.get("recording-list", []) or []

        if not recordings:
            return {}

        # Escogemos el primer resultado con release-list si existe.
        selected = None

        for recording in recordings:
            if recording.get("release-list"):
                selected = recording
                break

        if selected is None:
            selected = recordings[0]

        release_metadata = _extract_release_metadata(selected)

        found_title = _safe_str(selected.get("title")) or title
        found_artist = _artist_from_credit(selected, fallback=artist)

        recording_genre = _first_tag_name(selected)

        metadata = {
            "title": found_title,
            "artist": found_artist,
            "album_artist": found_artist,
            "album": release_metadata.get("album", ""),
            "year": release_metadata.get("year", ""),
            "track_number": release_metadata.get("track_number", ""),
            "disc_number": release_metadata.get("disc_number", "1") or "1",
            "genre": release_metadata.get("genre") or recording_genre,
            "release_mbid": release_metadata.get("release_mbid", ""),
        }

        return metadata

    except Exception:
        return {}


def search_cover_art_by_release_mbid(release_mbid: str) -> Optional[str]:
    """
    Devuelve URL de carátula usando un release MBID.
    """
    release_mbid = _safe_str(release_mbid)

    if not release_mbid:
        return None

    return f"https://coverartarchive.org/release/{release_mbid}/front"


def search_cover_art(artist: str, album: str) -> Optional[str]:
    """
    Busca carátula por artista + álbum.
    """
    artist = _safe_str(artist)
    album = _safe_str(album)

    if not artist or not album:
        return None

    try:
        result = musicbrainzngs.search_releases(
            artist=artist,
            release=album,
            limit=1,
        )

        releases = result.get("release-list", []) or []

        if not releases:
            return None

        mbid = releases[0].get("id")

        if not mbid:
            return None

        return f"https://coverartarchive.org/release/{mbid}/front"

    except Exception:
        return None


def download_cover(url: str, destination: Path) -> Optional[Path]:
    """
    Descarga una carátula.
    """
    if not url:
        return None

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

        return destination

    except Exception:
        return None