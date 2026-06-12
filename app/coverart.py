from pathlib import Path
from typing import Optional
import re

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

    MusicBrainz no siempre devuelve género. Primero miramos genre-list y luego tag-list.
    """
    if not entity:
        return ""

    genre_list = entity.get("genre-list", []) or []
    if genre_list:
        name = genre_list[0].get("name")
        if name:
            return _safe_str(name)

    tag_list = entity.get("tag-list", []) or []
    if tag_list:
        # Preferimos el tag con más votos si MusicBrainz incluye count.
        sorted_tags = sorted(
            tag_list,
            key=lambda item: int(item.get("count", 0) or 0),
            reverse=True,
        )
        name = sorted_tags[0].get("name")
        if name:
            return _safe_str(name)

    return ""


def _artist_from_credit(recording: dict, fallback: str = "") -> str:
    artist_credit = recording.get("artist-credit", []) or []

    if not artist_credit:
        return fallback

    parts = []

    for credit in artist_credit:
        if isinstance(credit, dict):
            artist_obj = credit.get("artist", {}) or {}
            name = artist_obj.get("name")
            if name:
                parts.append(name)
        elif isinstance(credit, str):
            # Separadores tipo " feat. ", " & ", etc.
            parts.append(credit)

    joined = "".join(parts).strip()
    return joined or fallback


def _parse_track_number_from_text(text: str) -> str:
    """
    Fallback cuando MusicBrainz no devuelve pista.

    Ejemplos soportados:
    - "01 - Canción" -> 1
    - "1. Canción" -> 1
    - "Track 03 - Canción" -> 3
    - "03 Canción" -> 3
    """
    text = _safe_str(text)

    if not text:
        return ""

    patterns = [
        r"^\s*(\d{1,3})\s*[-_.]\s+",
        r"^\s*(\d{1,3})\s+[-_.]\s*",
        r"^\s*(\d{1,3})\.\s+",
        r"\btrack\s*(\d{1,3})\b",
        r"^\s*(\d{1,3})\s+",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return str(int(match.group(1)))

    return ""


def _recording_id(recording: dict) -> str:
    return _safe_str(recording.get("id"))


def _release_score(release: dict, requested_artist: str = "", requested_title: str = "") -> int:
    """
    Heurística simple para escoger el release más útil.
    No pretende ser perfecta; prioriza releases con fecha, título y medios/pistas.
    """
    score = 0

    if release.get("date"):
        score += 10

    if release.get("title"):
        score += 5

    if release.get("medium-list"):
        score += 20

    status = _safe_str(release.get("status")).lower()
    if status == "official":
        score += 10

    release_group = release.get("release-group", {}) or {}
    primary_type = _safe_str(release_group.get("primary-type")).lower()
    if primary_type == "album":
        score += 8
    elif primary_type == "single":
        score += 5

    return score


def _lookup_release(release_mbid: str) -> dict:
    """
    Hace lookup detallado del release para poder recorrer medium-list/track-list.
    """
    if not release_mbid:
        return {}

    try:
        result = musicbrainzngs.get_release_by_id(
            release_mbid,
            includes=["recordings", "artists", "media", "release-groups", "tags", "genres"],
        )
        return result.get("release", {}) or {}
    except Exception:
        return {}


def _extract_track_from_release(
    release: dict,
    recording: dict,
) -> dict:
    """
    Busca la grabación dentro del tracklist de un release detallado.
    Devuelve album/year/track/disc si encuentra coincidencia.
    """
    recording_id = _recording_id(recording)

    album = _safe_str(release.get("title"))
    release_mbid = _safe_str(release.get("id"))
    date = _safe_str(release.get("date"))
    year = date[:4] if date else ""
    release_genre = _first_tag_name(release)

    best = {
        "album": album,
        "year": year,
        "track_number": "",
        "disc_number": "1",
        "release_mbid": release_mbid,
        "genre": release_genre,
    }

    medium_list = release.get("medium-list", []) or []

    for medium in medium_list:
        disc_number = _safe_str(medium.get("position")) or "1"
        track_list = medium.get("track-list", []) or []

        for track in track_list:
            track_recording = track.get("recording", {}) or {}
            track_recording_id = _safe_str(track_recording.get("id"))

            # Coincidencia fuerte por recording MBID.
            if recording_id and track_recording_id and recording_id == track_recording_id:
                track_number = _safe_str(track.get("position")) or _safe_str(track.get("number"))

                best.update(
                    {
                        "track_number": track_number,
                        "disc_number": disc_number,
                        "genre": release_genre or _first_tag_name(track_recording),
                    }
                )
                return best

        # Si no hay recording-id, intentamos coincidencia suave por título.
        requested_title = _safe_str(recording.get("title")).lower()
        if requested_title:
            for track in track_list:
                track_title = _safe_str(track.get("title")).lower()
                if track_title and track_title == requested_title:
                    track_number = _safe_str(track.get("position")) or _safe_str(track.get("number"))
                    best.update(
                        {
                            "track_number": track_number,
                            "disc_number": disc_number,
                            "genre": release_genre,
                        }
                    )
                    return best

    return best


def _extract_release_metadata_deep(recording: dict, requested_artist: str = "", requested_title: str = "") -> dict:
    """
    Extrae álbum/año/pista/disco/género con lookup profundo.

    Flujo:
    1. Usa release-list del recording search.
    2. Ordena releases con una pequeña heurística.
    3. Hace lookup detallado de cada release candidato.
    4. Recorre medium-list/track-list buscando el recording id.
    5. Devuelve track_number y disc_number si encuentra coincidencia.
    """
    releases = recording.get("release-list", []) or []

    fallback = {
        "album": "",
        "year": "",
        "track_number": "",
        "disc_number": "1",
        "release_mbid": "",
        "genre": "",
    }

    if not releases:
        return fallback

    # Fallback rápido con el primer release que tenga datos básicos.
    for release in releases:
        if release.get("title") or release.get("date"):
            date = _safe_str(release.get("date"))
            fallback.update(
                {
                    "album": _safe_str(release.get("title")),
                    "year": date[:4] if date else "",
                    "release_mbid": _safe_str(release.get("id")),
                    "genre": _first_tag_name(release),
                }
            )
            break

    sorted_releases = sorted(
        releases,
        key=lambda release: _release_score(release, requested_artist, requested_title),
        reverse=True,
    )

    # Limitamos candidatos para no castigar demasiado la API.
    for release_summary in sorted_releases[:5]:
        release_mbid = _safe_str(release_summary.get("id"))

        if not release_mbid:
            continue

        detailed_release = _lookup_release(release_mbid)
        if not detailed_release:
            continue

        metadata = _extract_track_from_release(detailed_release, recording)

        # Si encontramos número de pista, devolvemos este release.
        if metadata.get("track_number"):
            return metadata

        # Si no hay pista, pero mejora fallback, lo conservamos.
        if metadata.get("album") or metadata.get("year"):
            fallback.update({key: value for key, value in metadata.items() if value})

    return fallback


def search_musicbrainz_metadata(artist: str, title: str) -> dict:
    """
    Busca metadatos de una canción en MusicBrainz.

    Devuelve:
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
            limit=8,
        )

        recordings = result.get("recording-list", []) or []

        if not recordings:
            return {}

        # Preferimos resultados con release-list.
        selected = None
        for recording in recordings:
            if recording.get("release-list"):
                selected = recording
                break

        if selected is None:
            selected = recordings[0]

        found_title = _safe_str(selected.get("title")) or title
        found_artist = _artist_from_credit(selected, fallback=artist)
        recording_genre = _first_tag_name(selected)

        release_metadata = _extract_release_metadata_deep(
            selected,
            requested_artist=artist,
            requested_title=title,
        )

        fallback_track = _parse_track_number_from_text(title) or _parse_track_number_from_text(found_title)

        metadata = {
            "title": found_title,
            "artist": found_artist,
            "album_artist": found_artist,
            "album": release_metadata.get("album", ""),
            "year": release_metadata.get("year", ""),
            "track_number": release_metadata.get("track_number") or fallback_track,
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
