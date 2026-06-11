from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.coverart import download_cover, search_cover_art, search_musicbrainz_metadata
from app.database import Base, SessionLocal, engine, get_db
from app.downloader import download_audio, get_video_info
from app.jellyfin import jellyfin_configured, refresh_jellyfin_library
from app.library import organize_audio
from app.metadata import apply_audio_metadata
from app.models import DownloadHistory


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="dwSongs Docker Edition",
    version="1.1.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

executor = ThreadPoolExecutor(max_workers=2)


def row_to_dict(item: DownloadHistory) -> dict:
    return {
        "id": item.id,
        "url": item.url,
        "status": item.status,
        "error_message": item.error_message,
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
        "jellyfin_sent": item.jellyfin_sent,
        "duplicate": item.duplicate,
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


def process_download(history_id: int) -> None:
    db = SessionLocal()

    try:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
        if not item:
            return

        item.status = "getting_info"
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

        downloaded = download_audio(item.url, item.audio_format or "mp3")

        item.downloaded_path = str(downloaded)
        item.status = "downloaded"
        item.updated_at = datetime.utcnow()
        db.commit()

    except Exception as exc:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
        if item:
            item.status = "error"
            item.error_message = str(exc)
            item.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    items = db.query(DownloadHistory).order_by(DownloadHistory.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "items": items,
            "jellyfin_configured": jellyfin_configured(),
            "settings": settings,
        },
    )


@app.post("/downloads")
def create_downloads(
    urls: str = Form(...),
    audio_format: str = Form("mp3"),
    db: Session = Depends(get_db),
):
    created_ids = []

    clean_urls = [
        line.strip()
        for line in urls.replace(",", "\n").splitlines()
        if line.strip()
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

        created_ids.append(item.id)
        executor.submit(process_download, item.id)

    return RedirectResponse(url="/", status_code=303)


@app.post("/api/rows/{history_id}/update")
def update_row(
    history_id: int,
    title: str = Form(""),
    artist: str = Form(""),
    album_artist: str = Form(""),
    album: str = Form(""),
    year: str = Form(""),
    genre: str = Form(""),
    track_number: str = Form(""),
    disc_number: str = Form(""),
    comments: str = Form(""),
    lyrics: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()

    if not item:
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    item.title = title
    item.artist = artist
    item.album_artist = album_artist
    item.album = album
    item.year = year
    item.genre = genre
    item.track_number = track_number
    item.disc_number = disc_number
    item.comments = comments
    item.lyrics = lyrics
    item.updated_at = datetime.utcnow()

    db.commit()

    return {"ok": True, "item": row_to_dict(item)}


@app.post("/api/rows/{history_id}/auto-metadata")
def auto_metadata(history_id: int, db: Session = Depends(get_db)):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()

    if not item:
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

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
        item.disc_number = metadata.get("disc_number") or item.disc_number

    item.updated_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "item": row_to_dict(item)}


@app.post("/api/rows/{history_id}/upload-cover")
async def upload_cover(
    history_id: int,
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()

    if not item:
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    cover_path = settings.CONFIG_PATH / "covers" / f"{history_id}.jpg"
    cover_path.parent.mkdir(parents=True, exist_ok=True)
    cover_path.write_bytes(await cover.read())

    item.cover_path = str(cover_path)
    item.updated_at = datetime.utcnow()
    db.commit()

    return {"ok": True, "item": row_to_dict(item)}


@app.post("/api/rows/{history_id}/save-library")
def save_to_library(history_id: int, db: Session = Depends(get_db)):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()

    if not item:
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    if not item.downloaded_path:
        return JSONResponse({"ok": False, "error": "El fichero todavía no está descargado"}, status_code=400)

    downloaded_path = Path(item.downloaded_path)

    if not downloaded_path.exists():
        return JSONResponse({"ok": False, "error": "No existe el fichero descargado"}, status_code=400)

    item.status = "tagging"
    item.updated_at = datetime.utcnow()
    db.commit()

    metadata = {
        "title": item.title,
        "artist": item.artist,
        "album_artist": item.album_artist,
        "album": item.album,
        "year": item.year,
        "genre": item.genre,
        "track_number": item.track_number,
        "disc_number": item.disc_number,
        "comments": item.comments,
        "lyrics": item.lyrics,
    }

    cover_path = Path(item.cover_path) if item.cover_path else None

    if not cover_path:
        cover_url = search_cover_art(item.artist or "", item.album or "")
        if cover_url:
            cover_path = download_cover(
                cover_url,
                settings.CONFIG_PATH / "covers" / f"{history_id}.jpg",
            )

    apply_audio_metadata(downloaded_path, metadata, cover_path)

    final_path, duplicate = organize_audio(downloaded_path, metadata, cover_path)

    item.final_path = str(final_path)
    item.cover_path = str(cover_path) if cover_path else None
    item.duplicate = duplicate
    item.status = "ready_for_jellyfin"
    item.updated_at = datetime.utcnow()
    db.commit()

    if settings.AUTO_REFRESH_JELLYFIN:
        refresh_jellyfin_library()
        item.jellyfin_sent = True
        item.status = "sent_to_jellyfin"
        item.updated_at = datetime.utcnow()
        db.commit()

    return {"ok": True, "item": row_to_dict(item)}


@app.post("/api/rows/{history_id}/send-jellyfin")
def send_to_jellyfin(history_id: int, db: Session = Depends(get_db)):
    item = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()

    if not item:
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    success = refresh_jellyfin_library()

    if success:
        item.jellyfin_sent = True
        item.status = "sent_to_jellyfin"
        item.updated_at = datetime.utcnow()
        db.commit()

    return {"ok": success, "item": row_to_dict(item)}


@app.post("/api/bulk/send-jellyfin")
async def bulk_send_jellyfin(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    ids = payload.get("ids", [])

    success = refresh_jellyfin_library()

    if success:
        items = db.query(DownloadHistory).filter(DownloadHistory.id.in_(ids)).all()
        for item in items:
            item.jellyfin_sent = True
            item.status = "sent_to_jellyfin"
            item.updated_at = datetime.utcnow()
        db.commit()

    return {"ok": success}


@app.get("/api/history")
def api_history(db: Session = Depends(get_db)):
    items = db.query(DownloadHistory).order_by(DownloadHistory.created_at.desc()).all()
    return [row_to_dict(item) for item in items]


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "dwSongs Docker Edition",
    }


@app.get("/favicon.ico")
def favicon():
    return JSONResponse({}, status_code=204)