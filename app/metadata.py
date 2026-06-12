from pathlib import Path

from mutagen import File
from mutagen.id3 import APIC, COMM, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK, USLT


def apply_audio_metadata(
    file_path: Path,
    metadata: dict,
    cover_path: Path | None = None,
) -> None:
    audio = File(file_path, easy=False)

    if audio is None:
        return

    suffix = file_path.suffix.lower()

    if suffix == ".mp3":
        if audio.tags is None:
            audio.add_tags()

        tags = audio.tags

        if metadata.get("title"):
            tags["TIT2"] = TIT2(encoding=3, text=metadata["title"])

        if metadata.get("artist"):
            tags["TPE1"] = TPE1(encoding=3, text=metadata["artist"])

        if metadata.get("album_artist"):
            tags["TPE2"] = TPE2(encoding=3, text=metadata["album_artist"])

        if metadata.get("album"):
            tags["TALB"] = TALB(encoding=3, text=metadata["album"])

        if metadata.get("year"):
            tags["TDRC"] = TDRC(encoding=3, text=metadata["year"])

        if metadata.get("genre"):
            tags["TCON"] = TCON(encoding=3, text=metadata["genre"])

        if metadata.get("track_number"):
            tags["TRCK"] = TRCK(encoding=3, text=metadata["track_number"])

        if metadata.get("disc_number"):
            tags["TPOS"] = TPOS(encoding=3, text=metadata["disc_number"])

        if metadata.get("comments"):
            tags["COMM"] = COMM(
                encoding=3,
                lang="spa",
                desc="Comentarios",
                text=metadata["comments"],
            )

        if metadata.get("lyrics"):
            tags["USLT"] = USLT(
                encoding=3,
                lang="spa",
                desc="Letras",
                text=metadata["lyrics"],
            )

        if cover_path and cover_path.exists():
            tags["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_path.read_bytes(),
            )

        audio.save()
        return

    easy_audio = File(file_path, easy=True)

    if easy_audio is None:
        return

    mapping = {
        "title": "title",
        "artist": "artist",
        "album_artist": "albumartist",
        "album": "album",
        "year": "date",
        "genre": "genre",
        "track_number": "tracknumber",
        "disc_number": "discnumber",
        "comments": "comment",
        "lyrics": "lyrics",
    }

    for key, tag_name in mapping.items():
        value = metadata.get(key)
        if value:
            easy_audio[tag_name] = value

    easy_audio.save()