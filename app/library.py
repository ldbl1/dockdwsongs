from pathlib import Path
import re
import shutil
import unicodedata

from app.config import settings


INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'


def remove_accents(value: str) -> str:
    """
    Convierte texto con tildes a texto sin tildes.

    Ejemplos:
    - Rosalía -> Rosalia
    - Tú Me Dejaste -> Tu Me Dejaste
    """
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)

    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )


def remove_emojis_and_symbols(value: str) -> str:
    """
    Elimina emojis y símbolos no adecuados para nombres de fichero.
    Mantiene letras, números, espacios y puntuación básica.
    """
    if not value:
        return ""

    cleaned = []

    for char in value:
        category = unicodedata.category(char)

        # So = Symbol, other. Aquí suelen caer emojis/pictogramas.
        if category.startswith("So"):
            continue

        cleaned.append(char)

    return "".join(cleaned)


def sanitize_filename(value: str, fallback: str = "Unknown") -> str:
    """
    Limpia una cadena para usarla como carpeta o fichero.

    Elimina:
    - tildes
    - emojis
    - caracteres inválidos de Windows/Linux
    - saltos de línea
    - espacios repetidos
    """
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


def normalize_track_number(value: str | None) -> str:
    """
    Normaliza número de pista.

    Ejemplos:
    - None -> 01
    - "" -> 01
    - "1" -> 01
    - "01" -> 01
    - "1/12" -> 01
    """
    if not value:
        return "01"

    value = str(value).strip()

    if "/" in value:
        value = value.split("/", 1)[0]

    digits = re.sub(r"\D", "", value)

    if not digits:
        return "01"

    return digits.zfill(2)


def unique_path(path: Path) -> tuple[Path, bool]:
    """
    Evita sobrescribir ficheros.

    Si existe:
    01 - Cancion.mp3

    crea:
    01 - Cancion (2).mp3
    """
    if not path.exists():
        return path, False

    counter = 2

    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")

        if not candidate.exists():
            return candidate, True

        counter += 1


def get_library_music_path(metadata: dict | None = None) -> Path:
    """
    Ruta interna donde dwSongs escribe música para Jellyfin.

    Por defecto:
    /library/music

    Más adelante main.py podrá pasar metadata["library_music_path"]
    desde Settings.
    """
    metadata = metadata or {}

    configured_path = metadata.get("library_music_path")

    if configured_path:
        return Path(configured_path)

    return settings.LIBRARY_MUSIC_PATH


def build_library_destination(
    source_path: Path,
    metadata: dict,
) -> tuple[Path, bool]:
    """
    Construye ruta Jellyfin:

    /library/music/Music/{Artist}/{Album}/{TrackNumber} - {Title}.mp3
    """
    library_music_path = get_library_music_path(metadata)

    artist = sanitize_filename(
        metadata.get("artist") or metadata.get("uploader") or "Unknown Artist",
        fallback="Unknown Artist",
    )

    album = sanitize_filename(
        metadata.get("album") or "Unknown Album",
        fallback="Unknown Album",
    )

    title = sanitize_filename(
        metadata.get("title") or metadata.get("original_title") or source_path.stem,
        fallback=source_path.stem,
    )

    track_number = normalize_track_number(metadata.get("track_number"))

    destination_dir = (
        library_music_path
        / "Music"
        / artist
        / album
    )

    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / f"{track_number} - {title}{source_path.suffix.lower()}"
    destination, duplicate = unique_path(destination)

    return destination, duplicate


def copy_to_library(
    source_path: Path,
    metadata: dict,
) -> tuple[Path, bool]:
    """
    Envía un fichero a la biblioteca de Jellyfin.

    IMPORTANTE:
    - Copia el fichero a /library/music/Music/...
    - Si la copia va bien, elimina el fichero original de incoming.
    - Así evitamos duplicados entre incoming y biblioteca.
    """
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"No existe el fichero de origen: {source_path}")

    destination, duplicate = build_library_destination(source_path, metadata)

    destination.parent.mkdir(parents=True, exist_ok=True)

    # Si origen y destino fueran iguales, no hacemos nada destructivo.
    if source_path.resolve() == destination.resolve():
        return destination, duplicate

    shutil.copy2(source_path, destination)

    # Si la copia existe y tiene tamaño, borramos incoming.
    if destination.exists() and destination.stat().st_size > 0:
        try:
            source_path.unlink()
        except FileNotFoundError:
            pass

    return destination, duplicate


def move_to_library(
    source_path: Path,
    metadata: dict,
) -> tuple[Path, bool]:
    """
    Mueve un fichero a la biblioteca de Jellyfin.

    Ahora mismo el flujo principal usa copy_to_library(),
    que copia y luego elimina incoming tras validar la copia.
    """
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"No existe el fichero de origen: {source_path}")

    destination, duplicate = build_library_destination(source_path, metadata)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source_path.resolve() == destination.resolve():
        return destination, duplicate

    shutil.move(str(source_path), destination)

    return destination, duplicate


def delete_file_if_exists(path_value: str | None) -> bool:
    """
    Borra un fichero si existe.
    Devuelve True si borró algo.
    """
    if not path_value:
        return False

    path = Path(path_value)

    try:
        if path.exists() and path.is_file():
            path.unlink()
            return True
    except Exception:
        return False

    return False