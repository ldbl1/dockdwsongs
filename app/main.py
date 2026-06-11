from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import json

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.coverart import search_musicbrainz_metadata
from app.database import Base, SessionLocal, engine, get_db
from app.downloader import download_audio, get_video_info
from app.jellyfin import refresh_jellyfin_library, test_jellyfin_connection
from app.models import DownloadHistory


app = FastAPI(
    title="dwSongs Docker Edition",
    version="1.3.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

executor = ThreadPoolExecutor(max_workers=2)


SUPPORTED_LANGUAGES = {
    "es": "Español",
    "en": "English",
}


TRANSLATIONS = {
    "es": {
        "app_subtitle": "Docker Edition · Audio Manager",
        "home": "Inicio",
        "settings": "Ajustes",
        "jellyfin_configured": "Jellyfin configurado",
        "jellyfin_not_configured": "Jellyfin sin configurar",
        "new_download": "Nueva descarga",
        "new_download_help": "Añade una o varias URLs de YouTube. Una por línea.",
        "youtube_urls": "URLs de YouTube",
        "audio_format": "Formato audio",
        "add_to_queue": "Añadir a la cola",
        "history_title": "Histórico y cola",
        "history_help": "Edita los datos directamente en la tabla y guarda los cambios.",
        "refresh": "Actualizar",
        "send_selected": "Enviar seleccionados a Jellyfin",
        "status": "Estado",
        "title": "Título",
        "artist": "Artista",
        "album": "Álbum",
        "year": "Año",
        "track": "Pista",
        "genre": "Género",
        "format": "Formato",
        "jellyfin": "Jellyfin",
        "actions": "Acciones",
        "save": "Guardar",
        "search_data": "Buscar datos",
        "send": "Enviar",
        "delete": "Eliminar",
        "sent": "Enviado",
        "pending": "Pendiente",
        "empty_history": "Todavía no hay descargas.",
        "settings_title": "Ajustes",
        "settings_help": "Configura Jellyfin e idioma.",
        "jellyfin_url": "URL de Jellyfin",
        "jellyfin_api_key": "API Key de Jellyfin",
        "auto_refresh": "Refrescar Jellyfin automáticamente",
        "language": "Idioma",
        "save_settings": "Guardar ajustes",
        "test_connection": "Probar conexión",
        "back": "Volver",
        "settings_saved": "Ajustes guardados.",
        "test_ok": "Conexión correcta con Jellyfin.",
        "test_fail": "No se pudo conectar con Jellyfin.",
    },
    "en": {
        "app_subtitle": "Docker Edition · Audio Manager",
        "home": "Home",
        "settings": "Settings",
        "jellyfin_configured": "Jellyfin configured",
        "jellyfin_not_configured": "Jellyfin not configured",
        "new_download": "New download",
        "new_download_help": "Add one or more YouTube URLs. One per line.",
        "youtube_urls": "YouTube URLs",
        "audio_format": "Audio format",
        "add_to_queue": "Add to queue",
        "history_title": "History and queue",
        "history_help": "Edit metadata directly in the table and save changes.",
        "refresh": "Refresh",
        "send_selected": "Send selected to Jellyfin",
        "status": "Status",
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "year": "Year",
        "track": "Track",
        "genre": "Genre",
        "format": "Format",
        "jellyfin": "Jellyfin",
        "actions": "Actions",
        "save": "Save",
        "search_data": "Search data",
        "send": "Send",
        "delete": "Delete",
        "sent": "Sent",
        "pending": "Pending",
        "empty_history": "No downloads yet.",
        "settings_title": "Settings",
        "settings_help": "Configure Jellyfin and language.",
        "jellyfin_url": "Jellyfin URL",
        "jellyfin_api_key": "Jellyfin API Key",
        "auto_refresh": "Refresh Jellyfin automatically",
        "language": "Language",
        "save_settings": "Save settings",
        "test_connection": "Test connection",
        "back": "Back",
        "settings_saved": "Settings saved.",
        "test_ok": "Jellyfin connection OK.",
        "test_fail": "Could not connect to Jellyfin.",
    },
}


def config_file() -> Path:
    return settings.CONFIG_PATH / "settings.json"


def load_config() -> dict:
    data = {
        "jellyfin_url": settings.JELLYFIN_URL or "",
        "jellyfin_api_key": settings.JELLYFIN_API_KEY or "",
        "auto_refresh": bool(settings.AUTO_REFRESH_JELLYFIN),
        "language": "es",
    }

    path = config_file()

    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            data.update(saved)
        except Exception:
            pass

    if data.get("language") not in SUPPORTED_LANGUAGES:
        data["language"] = "es"

    return data


def save_config(data: dict) -> None:
    settings.CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    config_file().write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_texts() -> dict:
    config = load_config()
    return TRANSLATIONS.get(config["language"], TRANSLATIONS["es"])


def is_jellyfin_configured() -> bool:
    config = load_config()
    return bool(config.get("jellyfin_url") and config.get("jellyfin_api_key"))


def row_to_dict(item: DownloadHistory) -> dict:
    return {
        "id": item.id,
        "url": item.url or "",
        "status": item.status or "",
        "error_message": item.error_message or "",
        "title": item.title or "",
        "artist": item.artist or "",
        "album_artist": item.album_artist or "",
        "album": item.album or "",
        "year": item.year or "",
        "genre": item.genre or "",
        "track_number": item.track_number or "",
        "disc_number": item.disc_number or "",
        "comments": item.comments or "",
        "lyrics": item.lyrics or "",
        "audio_format": item.audio_format or "mp3",
        "downloaded_path": item.downloaded_path or "",
        "final_path": item.final_path or "",
        "cover_path": item.cover_path or "",
        "jellyfin_sent": bool(item.jellyfin_sent),
        "duplicate": bool(item.duplicate),
    }


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
def shutdown():
    executor.shutdown(wait=False)


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    items = (
        db.query(DownloadHistory)
        .order_by(DownloadHistory.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "items": items,
            "config": load_config(),
            "t": get_texts(),
            "jellyfin_configured": is_jellyfin_configured(),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    saved: str = "",
    tested: str = "",
):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "config": load_config(),
            "languages": SUPPORTED_LANGUAGES,
            "t": get_texts(),
            "jellyfin_configured": is_jellyfin_configured(),
            "saved": saved == "1",
            "tested": tested,
        },
    )


@app.post("/settings")
def save_settings(
    jellyfin_url: str = Form(""),
    jellyfin_api_key: str = Form(""),
    auto_refresh: str | None = Form(None),
    language: str = Form("es"),
):
    save_config(
        {
            "jellyfin_url": jellyfin_url.strip(),
            "jellyfin_api_key": jellyfin_api_key.strip(),
            "auto_refresh": auto_refresh == "on",
            "language": language if language in SUPPORTED_LANGUAGES else "es",
        }
    )

    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/test")
def test_settings(
    jellyfin_url: str = Form(""),
    jellyfin_api_key: str = Form(""),
    auto_refresh: str | None = Form(None),
    language: str = Form("es"),
):
    save_config(
        {
            "jellyfin_url": jellyfin_url.strip(),
            "jellyfin_api_key": jellyfin_api_key.strip(),
            "auto_refresh": auto_refresh == "on",
            "language": language if language in SUPPORTED_LANGUAGES else "es",
        }
    )

    ok = test_jellyfin_connection(
        jellyfin_url.strip(),
        jellyfin_api_key.strip(),
    )

    return RedirectResponse(
        f"/settings?tested={'ok' if ok else 'fail'}",
        status_code=303,
    )


def process_download(download_id: int):
    db = SessionLocal()

    try:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if not item:
            return

        item.status = "getting_info"
        item.error_message = None
        item.updated_at = datetime.utcnow()
        db.commit()

        info = get_video_info(item.url)

        item.title = item.title or info.get("title") or ""
        item.artist = item.artist or info.get("uploader") or ""
        item.album_artist = item.album_artist or item.artist or ""
        item.comments = item.comments or item.url
        item.status = "downloading"
        item.updated_at = datetime.utcnow()
        db.commit()

        file_path = download_audio(
            item.url,
            item.audio_format or "mp3",
        )

        item.downloaded_path = str(file_path)
        item.status = "downloaded"
        item.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if item:
            item.status = "error"
            item.error_message = str(e)
            item.updated_at = datetime.utcnow()
            db.commit()

    finally:
        db.close()


@app.post("/downloads")
def create_download(
    urls: str = Form(...),
    audio_format: str = Form("mp3"),
    db: Session = Depends(get_db),
):
    clean_urls = [
        url.strip()
        for url in urls.replace(",", "\n").splitlines()
        if url.strip()
    ]

    for url in clean_urls:
        item = DownloadHistory(
            url=url,
            audio_format=audio_format,
            status="queued",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        executor.submit(process_download, item.id)

    return RedirectResponse("/", status_code=303)


@app.post("/api/rows/{download_id}/update")
def update_row(
    download_id: int,
    title: str = Form(""),
    artist: str = Form(""),
    album_artist: str = Form(""),
    album: str = Form(""),
    year: str = Form(""),
    genre: str = Form(""),
    track_number: str = Form(""),
    disc_number: str = Form("1"),
    comments: str = Form(""),
    lyrics: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item:
        return JSONResponse(
            {"ok": False, "error": "Registro no encontrado"},
            status_code=404,
        )

    item.title = title
    item.artist = artist
    item.album_artist = album_artist or artist
    item.album = album
    item.year = year
    item.genre = genre
    item.track_number = track_number
    item.disc_number = disc_number
    item.comments = comments
    item.lyrics = lyrics
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    return {
        "ok": True,
        "item": row_to_dict(item),
    }


@app.post("/api/rows/{download_id}/auto-metadata")
def auto_metadata(
    download_id: int,
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item:
        return JSONResponse(
            {"ok": False, "error": "Registro no encontrado"},
            status_code=404,
        )

    metadata = search_musicbrainz_metadata(
        artist=item.artist or "",
        title=item.title or "",
    )

    if metadata:
        item.title = metadata.get("title") or item.title
        item.artist = metadata.get("artist") or item.artist
        item.album_artist = metadata.get("artist") or item.album_artist
        item.album = metadata.get("album") or item.album
        item.year = metadata.get("year") or item.year
        item.genre = metadata.get("genre") or item.genre
        item.track_number = metadata.get("track_number") or item.track_number
        item.disc_number = metadata.get("disc_number") or item.disc_number or "1"

    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    return {
        "ok": True,
        "item": row_to_dict(item),
    }


@app.delete("/api/rows/{download_id}")
def delete_row(
    download_id: int,
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item:
        return JSONResponse(
            {"ok": False, "error": "Registro no encontrado"},
            status_code=404,
        )

    db.delete(item)
    db.commit()

    return {
        "ok": True,
        "deleted": download_id,
    }


@app.post("/api/jellyfin/send/{download_id}")
def send_jellyfin(
    download_id: int,
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item:
        return JSONResponse(
            {"ok": False, "error": "Registro no encontrado"},
            status_code=404,
        )

    config = load_config()

    ok = refresh_jellyfin_library(
        config.get("jellyfin_url", ""),
        config.get("jellyfin_api_key", ""),
    )

    if ok:
        item.jellyfin_sent = True
        item.status = "sent_to_jellyfin"
        item.updated_at = datetime.utcnow()
        db.commit()

    return {
        "ok": ok,
    }


@app.post("/api/jellyfin/send-selected")
async def send_selected_jellyfin(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()
    ids = payload.get("ids", [])

    if not ids:
        return JSONResponse(
            {"ok": False, "error": "No hay registros seleccionados"},
            status_code=400,
        )

    config = load_config()

    ok = refresh_jellyfin_library(
        config.get("jellyfin_url", ""),
        config.get("jellyfin_api_key", ""),
    )

    if ok:
        items = db.query(DownloadHistory).filter(DownloadHistory.id.in_(ids)).all()

        for item in items:
            item.jellyfin_sent = True
            item.status = "sent_to_jellyfin"
            item.updated_at = datetime.utcnow()

        db.commit()

    return {
        "ok": ok,
    }


@app.get("/api/history")
def api_history(
    db: Session = Depends(get_db),
):
    items = (
        db.query(DownloadHistory)
        .order_by(DownloadHistory.id.desc())
        .all()
    )

    return [row_to_dict(item) for item in items]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "dwSongs Docker Edition",
        "version": "1.3.0",
    }


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)