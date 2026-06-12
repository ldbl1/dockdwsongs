from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import json

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    any_user_exists,
    attach_session_cookie,
    authenticate_user,
    clear_session_cookie,
    create_session,
    get_current_user,
    logout_current_session,
    require_admin,
    require_login,
)
from app.config import settings
from app.coverart import search_musicbrainz_metadata
from app.database import Base, SessionLocal, engine, get_db
from app.downloader import download_audio, get_video_info
from app.i18n_loader import get_supported_languages, load_language
from app.jellyfin import refresh_jellyfin_library
from app.library import copy_to_library, delete_file_if_exists
from app.models import DownloadAction, DownloadHistory, User
from app.security import (
    hash_password,
    is_valid_username,
    normalize_username,
    validate_password_strength,
)


app = FastAPI(
    title="dwSongs Docker Edition",
    version="1.5.0",
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

executor = ThreadPoolExecutor(max_workers=2)


# -----------------------------------------------------------------------------
# Configuración / idiomas
# -----------------------------------------------------------------------------

def config_file() -> Path:
    return settings.CONFIG_PATH / "settings.json"


def load_config() -> dict:
    data = {
        "jellyfin_url": settings.JELLYFIN_URL or "",
        "jellyfin_api_key": settings.JELLYFIN_API_KEY or "",
        "auto_refresh": bool(settings.AUTO_REFRESH_JELLYFIN),
        "language": "es",
        "library_music_path": str(settings.LIBRARY_MUSIC_PATH),
    }

    path = config_file()

    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)
        except Exception:
            pass

    if data.get("language") not in get_supported_languages():
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
    return load_language(config.get("language", "es"))


def is_jellyfin_configured() -> bool:
    config = load_config()
    return bool(config.get("jellyfin_url") and config.get("jellyfin_api_key"))


def refresh_jellyfin_from_config() -> bool:
    config = load_config()
    return refresh_jellyfin_library(
        config.get("jellyfin_url", ""),
        config.get("jellyfin_api_key", ""),
    )


def common_context(request: Request, db: Session, extra: dict | None = None) -> dict:
    context = {
        "request": request,
        "config": load_config(),
        "t": get_texts(),
        "jellyfin_configured": is_jellyfin_configured(),
        "current_user": get_current_user(request, db),
    }

    if extra:
        context.update(extra)

    return context


# -----------------------------------------------------------------------------
# Utilidades auditoría / serialización
# -----------------------------------------------------------------------------

def add_action(
    db: Session,
    action: str,
    download_id: int | None = None,
    user_id: int | None = None,
    details: dict | str | None = None,
) -> None:
    if isinstance(details, dict):
        details_value = json.dumps(details, ensure_ascii=False)
    else:
        details_value = details

    db.add(
        DownloadAction(
            download_id=download_id,
            user_id=user_id,
            action=action,
            details=details_value,
            created_at=datetime.utcnow(),
        )
    )
    db.commit()


def file_size(path_value: str | None) -> int | None:
    if not path_value:
        return None

    try:
        path = Path(path_value)
        if path.exists() and path.is_file():
            return path.stat().st_size
    except Exception:
        return None

    return None


def row_to_dict(item: DownloadHistory) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "username": item.user.username if item.user else "",
        "url": item.url or "",
        "original_title": item.original_title or "",
        "uploader": item.uploader or "",
        "duration": item.duration,
        "thumbnail_url": item.thumbnail_url or "",
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
        "incoming_path": item.incoming_path or "",
        "downloaded_path": item.downloaded_path or "",
        "final_path": item.final_path or "",
        "cover_path": item.cover_path or "",
        "incoming_size_bytes": item.incoming_size_bytes,
        "final_size_bytes": item.final_size_bytes,
        "jellyfin_sent": bool(item.jellyfin_sent),
        "library_saved": bool(item.library_saved),
        "duplicate": bool(item.duplicate),
        "is_deleted": bool(item.is_deleted),
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
        "queued_at": item.queued_at.isoformat() if item.queued_at else "",
        "info_fetched_at": item.info_fetched_at.isoformat() if item.info_fetched_at else "",
        "download_started_at": item.download_started_at.isoformat() if item.download_started_at else "",
        "downloaded_at": item.downloaded_at.isoformat() if item.downloaded_at else "",
        "metadata_updated_at": item.metadata_updated_at.isoformat() if item.metadata_updated_at else "",
        "moved_to_library_at": item.moved_to_library_at.isoformat() if item.moved_to_library_at else "",
        "jellyfin_refreshed_at": item.jellyfin_refreshed_at.isoformat() if item.jellyfin_refreshed_at else "",
    }


# -----------------------------------------------------------------------------
# Startup / shutdown
# -----------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.on_event("shutdown")
def shutdown():
    executor.shutdown(wait=False)


# -----------------------------------------------------------------------------
# Auth: setup / login / logout
# -----------------------------------------------------------------------------

@app.get("/setup", response_class=HTMLResponse)
def setup_admin_page(request: Request, db: Session = Depends(get_db)):
    if any_user_exists(db):
        return RedirectResponse("/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="setup_admin.html",
        context=common_context(request, db, {"error": "", "message": ""}),
    )


@app.post("/setup")
def setup_admin_create(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    db: Session = Depends(get_db),
):
    if any_user_exists(db):
        return RedirectResponse("/login", status_code=303)

    username = normalize_username(username)

    valid_username, username_error = is_valid_username(username)
    if not valid_username:
        return templates.TemplateResponse(
            request=request,
            name="setup_admin.html",
            context=common_context(request, db, {"error": username_error, "message": ""}),
            status_code=400,
        )

    if password != password_confirm:
        return templates.TemplateResponse(
            request=request,
            name="setup_admin.html",
            context=common_context(request, db, {"error": "Las contraseñas no coinciden.", "message": ""}),
            status_code=400,
        )

    valid_password, password_error = validate_password_strength(password)
    if not valid_password:
        return templates.TemplateResponse(
            request=request,
            name="setup_admin.html",
            context=common_context(request, db, {"error": password_error, "message": ""}),
            status_code=400,
        )

    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=True,
        is_active=True,
        must_change_password=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    add_action(db, "admin_created", user_id=user.id, details={"username": user.username})

    session = create_session(db, user, request)
    response = RedirectResponse("/", status_code=303)
    attach_session_cookie(response, session)

    return response


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    error: str = "",
    message: str = "",
    db: Session = Depends(get_db),
):
    if not any_user_exists(db):
        return RedirectResponse("/setup", status_code=303)

    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=common_context(request, db, {"error": error, "message": message}),
    )


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    if not any_user_exists(db):
        return RedirectResponse("/setup", status_code=303)

    user = authenticate_user(db, username, password)

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=common_context(request, db, {"error": "Usuario o contraseña incorrectos.", "message": ""}),
            status_code=401,
        )

    add_action(db, "login", user_id=user.id, details={"username": user.username})

    session = create_session(db, user, request)
    response = RedirectResponse("/", status_code=303)
    attach_session_cookie(response, session)

    return response


@app.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    if user:
        add_action(db, "logout", user_id=user.id, details={"username": user.username})

    logout_current_session(request, db)

    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)

    return response


@app.get("/logout")
def logout_get(request: Request, db: Session = Depends(get_db)):
    return logout(request, db)


# -----------------------------------------------------------------------------
# Vistas principales
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    user = user_or_response

    query = (
        db.query(DownloadHistory)
        .options(joinedload(DownloadHistory.user))
        .filter(DownloadHistory.is_deleted.is_(False))
    )

    if not user.is_admin:
        query = query.filter(DownloadHistory.user_id == user.id)

    items = query.order_by(DownloadHistory.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=common_context(request, db, {"items": items}),
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(
    request: Request,
    saved: str = "",
    tested: str = "",
    db: Session = Depends(get_db),
):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context=common_context(
            request,
            db,
            {
                "languages": get_supported_languages(),
                "saved": saved == "1",
                "tested": tested,
            },
        ),
    )


@app.post("/settings")
def save_settings(
    request: Request,
    jellyfin_url: str = Form(""),
    jellyfin_api_key: str = Form(""),
    auto_refresh: str | None = Form(None),
    language: str = Form("es"),
    library_music_path: str = Form("/library/music"),
    db: Session = Depends(get_db),
):
    user_or_response = require_admin(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    supported_languages = get_supported_languages()

    save_config(
        {
            "jellyfin_url": jellyfin_url.strip(),
            "jellyfin_api_key": jellyfin_api_key.strip(),
            "auto_refresh": auto_refresh == "on",
            "language": language if language in supported_languages else "es",
            "library_music_path": library_music_path.strip() or "/library/music",
        }
    )

    add_action(db, "settings_updated", user_id=user_or_response.id)

    return RedirectResponse("/settings?saved=1", status_code=303)


@app.post("/settings/test")
def test_settings(
    request: Request,
    jellyfin_url: str = Form(""),
    jellyfin_api_key: str = Form(""),
    db: Session = Depends(get_db),
):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    ok = refresh_jellyfin_library(
        jellyfin_url.strip(),
        jellyfin_api_key.strip(),
    )

    return RedirectResponse(
        f"/settings?tested={'ok' if ok else 'fail'}",
        status_code=303,
    )


# -----------------------------------------------------------------------------
# Admin: usuarios
# -----------------------------------------------------------------------------

@app.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    error: str = "",
    message: str = "",
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    users = db.query(User).order_by(User.id.asc()).all()

    return templates.TemplateResponse(
        request=request,
        name="admin_users.html",
        context=common_context(
            request,
            db,
            {
                "users": users,
                "error": error,
                "message": message,
            },
        ),
    )


@app.post("/admin/users/create")
def admin_create_user(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    is_admin: str | None = Form(None),
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    username = normalize_username(username)

    valid_username, username_error = is_valid_username(username)
    if not valid_username:
        return RedirectResponse(f"/admin/users?error={username_error}", status_code=303)

    valid_password, password_error = validate_password_strength(password)
    if not valid_password:
        return RedirectResponse(f"/admin/users?error={password_error}", status_code=303)

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return RedirectResponse("/admin/users?error=El usuario ya existe", status_code=303)

    user = User(
        username=username,
        password_hash=hash_password(password),
        is_admin=is_admin == "on",
        is_active=True,
        must_change_password=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    add_action(
        db,
        "user_created",
        user_id=admin_or_response.id,
        details={"created_user": user.username, "is_admin": user.is_admin},
    )

    return RedirectResponse("/admin/users?message=Usuario creado", status_code=303)


@app.post("/admin/users/{user_id}/toggle-active")
def admin_toggle_user_active(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return RedirectResponse("/admin/users?error=Usuario no encontrado", status_code=303)

    if user.id == admin_or_response.id and user.is_active:
        return RedirectResponse("/admin/users?error=No puedes desactivarte a ti mismo", status_code=303)

    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.commit()

    add_action(
        db,
        "user_active_toggled",
        user_id=admin_or_response.id,
        details={"target_user": user.username, "is_active": user.is_active},
    )

    return RedirectResponse("/admin/users?message=Usuario actualizado", status_code=303)


@app.post("/admin/users/{user_id}/toggle-admin")
def admin_toggle_user_admin(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return RedirectResponse("/admin/users?error=Usuario no encontrado", status_code=303)

    if user.id == admin_or_response.id and user.is_admin:
        return RedirectResponse("/admin/users?error=No puedes quitarte admin a ti mismo", status_code=303)

    user.is_admin = not user.is_admin
    user.updated_at = datetime.utcnow()
    db.commit()

    add_action(
        db,
        "user_admin_toggled",
        user_id=admin_or_response.id,
        details={"target_user": user.username, "is_admin": user.is_admin},
    )

    return RedirectResponse("/admin/users?message=Permisos actualizados", status_code=303)


@app.post("/admin/users/{user_id}/reset-password")
def admin_reset_user_password(
    user_id: int,
    request: Request,
    new_password: str = Form(""),
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return RedirectResponse("/admin/users?error=Usuario no encontrado", status_code=303)

    valid_password, password_error = validate_password_strength(new_password)
    if not valid_password:
        return RedirectResponse(f"/admin/users?error={password_error}", status_code=303)

    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    user.updated_at = datetime.utcnow()
    db.commit()

    add_action(
        db,
        "password_reset",
        user_id=admin_or_response.id,
        details={"target_user": user.username},
    )

    return RedirectResponse("/admin/users?message=Contraseña reseteada", status_code=303)


# -----------------------------------------------------------------------------
# Admin: descargas globales
# -----------------------------------------------------------------------------

@app.get("/admin/downloads", response_class=HTMLResponse)
def admin_downloads_page(
    request: Request,
    error: str = "",
    message: str = "",
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    downloads = (
        db.query(DownloadHistory)
        .options(
            joinedload(DownloadHistory.user),
            joinedload(DownloadHistory.actions).joinedload(DownloadAction.user),
        )
        .order_by(DownloadHistory.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin_downloads.html",
        context=common_context(
            request,
            db,
            {
                "downloads": downloads,
                "error": error,
                "message": message,
            },
        ),
    )


# -----------------------------------------------------------------------------
# YouTube / cola / descarga
# -----------------------------------------------------------------------------

def fill_video_info(item: DownloadHistory) -> None:
    info = get_video_info(item.url)

    item.original_title = info.get("title") or item.original_title or ""
    item.uploader = info.get("uploader") or item.uploader or ""
    item.duration = info.get("duration")
    item.thumbnail_url = info.get("thumbnail") or item.thumbnail_url or ""

    item.title = item.title or item.original_title
    item.artist = item.artist or item.uploader
    item.album_artist = item.album_artist or item.artist
    item.comments = item.comments or item.url
    item.status = "ready"
    item.info_fetched_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()


def process_get_info(download_id: int) -> None:
    db = SessionLocal()

    try:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if not item:
            return

        item.status = "getting_info"
        item.error_message = None
        item.updated_at = datetime.utcnow()
        db.commit()

        fill_video_info(item)
        db.commit()

        add_action(db, "info_fetched", download_id=item.id, user_id=item.user_id)

    except Exception as e:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if item:
            item.status = "error"
            item.error_message = str(e)
            item.updated_at = datetime.utcnow()
            db.commit()
            add_action(db, "error", download_id=item.id, user_id=item.user_id, details=str(e))

    finally:
        db.close()


def process_download(download_id: int) -> None:
    db = SessionLocal()

    try:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if not item:
            return

        if not item.original_title:
            item.status = "getting_info"
            item.error_message = None
            item.updated_at = datetime.utcnow()
            db.commit()
            fill_video_info(item)
            db.commit()
            add_action(db, "info_fetched", download_id=item.id, user_id=item.user_id)

        item.status = "downloading"
        item.error_message = None
        item.download_started_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        db.commit()
        add_action(db, "download_started", download_id=item.id, user_id=item.user_id)

        file_path = download_audio(
            url=item.url,
            audio_format=item.audio_format or "mp3",
            preferred_title=item.original_title or item.title,
        )

        item.incoming_path = str(file_path)
        item.downloaded_path = str(file_path)
        item.incoming_size_bytes = file_size(str(file_path))
        item.status = "downloaded"
        item.downloaded_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        db.commit()
        add_action(
            db,
            "downloaded",
            download_id=item.id,
            user_id=item.user_id,
            details={"incoming_path": item.incoming_path, "size": item.incoming_size_bytes},
        )

    except Exception as e:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

        if item:
            item.status = "error"
            item.error_message = str(e)
            item.updated_at = datetime.utcnow()
            db.commit()
            add_action(db, "error", download_id=item.id, user_id=item.user_id, details=str(e))

    finally:
        db.close()


@app.post("/downloads")
def create_download(
    request: Request,
    urls: str = Form(...),
    audio_format: str = Form("mp3"),
    db: Session = Depends(get_db),
):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return user_or_response

    user = user_or_response

    clean_urls = [
        url.strip()
        for url in urls.replace(",", "\n").splitlines()
        if url.strip()
    ]

    for url in clean_urls:
        item = DownloadHistory(
            user_id=user.id,
            url=url,
            audio_format=audio_format,
            status="pending",
            queued_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        add_action(db, "queued", download_id=item.id, user_id=user.id, details={"url": url})
        executor.submit(process_get_info, item.id)

    return RedirectResponse("/", status_code=303)


@app.post("/api/queue")
async def create_queue_from_json(
    request: Request,
    db: Session = Depends(get_db),
):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    user = user_or_response
    payload = await request.json()
    rows = payload.get("rows", [])
    audio_format = payload.get("audio_format", "mp3")
    created = []

    for row in rows:
        url = (row.get("url") or "").strip()

        if not url:
            continue

        item = DownloadHistory(
            user_id=user.id,
            url=url,
            original_title=row.get("original_title") or "",
            uploader=row.get("uploader") or "",
            title=row.get("title") or row.get("original_title") or "",
            artist=row.get("artist") or row.get("uploader") or "",
            album_artist=row.get("artist") or row.get("uploader") or "",
            audio_format=audio_format,
            status="ready" if row.get("original_title") else "pending",
            queued_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        add_action(db, "queued", download_id=item.id, user_id=user.id, details={"url": url})
        created.append(row_to_dict(item))

        if not item.original_title:
            executor.submit(process_get_info, item.id)

    return {"ok": True, "created": created}


@app.post("/api/video-info")
async def api_video_info(request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    payload = await request.json()
    urls = payload.get("urls", [])
    results = []

    for url in urls:
        clean_url = (url or "").strip()

        if not clean_url:
            continue

        try:
            info = get_video_info(clean_url)
            results.append(
                {
                    "ok": True,
                    "url": clean_url,
                    "original_title": info.get("title") or "",
                    "uploader": info.get("uploader") or "",
                    "duration": info.get("duration"),
                    "thumbnail_url": info.get("thumbnail") or "",
                }
            )
        except Exception as e:
            results.append({"ok": False, "url": clean_url, "error": str(e)})

    return {"ok": True, "results": results}


@app.post("/api/rows/{download_id}/fetch-info")
def fetch_info_for_row(download_id: int, request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "No encontrado"}, status_code=404)

    executor.submit(process_get_info, download_id)
    return {"ok": True}


@app.post("/api/rows/{download_id}/download")
def download_row(download_id: int, request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "No encontrado"}, status_code=404)

    executor.submit(process_download, download_id)
    return {"ok": True}


@app.post("/api/rows/download-selected")
async def download_selected(request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    payload = await request.json()
    ids = payload.get("ids", [])

    for download_id in ids:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == int(download_id)).first()
        if item and (user_or_response.is_admin or item.user_id == user_or_response.id):
            executor.submit(process_download, int(download_id))

    return {"ok": True, "queued": ids}


@app.post("/api/rows/{download_id}/update")
def update_row(
    download_id: int,
    request: Request,
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
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    old_values = {
        "title": item.title,
        "artist": item.artist,
        "album": item.album,
        "year": item.year,
        "genre": item.genre,
        "track_number": item.track_number,
    }

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
    item.metadata_updated_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    add_action(
        db,
        "metadata_updated",
        download_id=item.id,
        user_id=user_or_response.id,
        details={"old": old_values, "new": {"title": title, "artist": artist, "album": album, "year": year, "genre": genre, "track_number": track_number}},
    )

    return {"ok": True, "item": row_to_dict(item)}


@app.post("/api/rows/{download_id}/auto-metadata")
def auto_metadata(download_id: int, request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    metadata = search_musicbrainz_metadata(
        artist=item.artist or item.uploader or "",
        title=item.title or item.original_title or "",
    )

    if metadata:
        item.title = metadata.get("title") or item.title
        item.artist = metadata.get("artist") or item.artist
        item.album_artist = metadata.get("album_artist") or metadata.get("artist") or item.album_artist
        item.album = metadata.get("album") or item.album
        item.year = metadata.get("year") or item.year
        item.genre = metadata.get("genre") or item.genre
        item.track_number = metadata.get("track_number") or item.track_number
        item.disc_number = metadata.get("disc_number") or item.disc_number or "1"

    item.metadata_updated_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(item)

    add_action(db, "metadata_auto_fetched", download_id=item.id, user_id=user_or_response.id, details=metadata)

    return {"ok": True, "item": row_to_dict(item)}


def send_item_to_library_and_jellyfin(item: DownloadHistory, db: Session, acting_user_id: int | None = None) -> bool:
    source_value = item.incoming_path or item.downloaded_path

    if not source_value:
        raise FileNotFoundError("No hay fichero descargado en incoming.")

    source_path = Path(source_value)

    if not source_path.exists():
        raise FileNotFoundError(f"No existe el fichero descargado: {source_path}")

    config = load_config()

    metadata = {
        "library_music_path": config.get("library_music_path") or str(settings.LIBRARY_MUSIC_PATH),
        "original_title": item.original_title,
        "title": item.title or item.original_title or source_path.stem,
        "artist": item.artist or item.uploader or "Unknown Artist",
        "uploader": item.uploader,
        "album": item.album or "Unknown Album",
        "track_number": item.track_number or "1",
    }

    item.status = "saving_library"
    item.updated_at = datetime.utcnow()
    db.commit()

    final_path, duplicate = copy_to_library(source_path=source_path, metadata=metadata)

    item.final_path = str(final_path)
    item.final_size_bytes = file_size(str(final_path))
    item.duplicate = duplicate
    item.library_saved = True
    item.incoming_path = None
    item.downloaded_path = None
    item.moved_to_library_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()

    db.commit()

    add_action(
        db,
        "moved_to_library",
        download_id=item.id,
        user_id=acting_user_id or item.user_id,
        details={"final_path": item.final_path, "duplicate": duplicate, "size": item.final_size_bytes},
    )

    refreshed = refresh_jellyfin_library(
        config.get("jellyfin_url", ""),
        config.get("jellyfin_api_key", ""),
    )

    if refreshed:
        item.jellyfin_sent = True
        item.status = "sent_to_jellyfin"
        item.jellyfin_refreshed_at = datetime.utcnow()
        add_action(db, "jellyfin_refreshed", download_id=item.id, user_id=acting_user_id or item.user_id)
    else:
        item.status = "library_saved"

    item.updated_at = datetime.utcnow()
    db.commit()

    return refreshed


@app.post("/api/jellyfin/send/{download_id}")
def send_jellyfin(download_id: int, request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    try:
        refreshed = send_item_to_library_and_jellyfin(item, db, acting_user_id=user_or_response.id)
        return {"ok": True, "jellyfin_refreshed": refreshed, "item": row_to_dict(item)}
    except Exception as e:
        item.status = "error"
        item.error_message = str(e)
        item.updated_at = datetime.utcnow()
        db.commit()
        add_action(db, "error", download_id=item.id, user_id=user_or_response.id, details=str(e))
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/jellyfin/send-selected")
async def send_selected_jellyfin(request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    payload = await request.json()
    ids = payload.get("ids", [])

    if not ids:
        return JSONResponse({"ok": False, "error": "No hay registros seleccionados"}, status_code=400)

    results = []

    for download_id in ids:
        item = db.query(DownloadHistory).filter(DownloadHistory.id == int(download_id)).first()

        if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
            results.append({"id": download_id, "ok": False, "error": "Registro no encontrado"})
            continue

        try:
            refreshed = send_item_to_library_and_jellyfin(item, db, acting_user_id=user_or_response.id)
            results.append({"id": download_id, "ok": True, "jellyfin_refreshed": refreshed})
        except Exception as e:
            item.status = "error"
            item.error_message = str(e)
            item.updated_at = datetime.utcnow()
            db.commit()
            add_action(db, "error", download_id=item.id, user_id=user_or_response.id, details=str(e))
            results.append({"id": download_id, "ok": False, "error": str(e)})

    return {"ok": True, "results": results}


@app.delete("/api/rows/{download_id}")
def delete_row(
    download_id: int,
    request: Request,
    force: bool = False,
    db: Session = Depends(get_db),
):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    item = db.query(DownloadHistory).filter(DownloadHistory.id == download_id).first()

    if not item or (not user_or_response.is_admin and item.user_id != user_or_response.id):
        return JSONResponse({"ok": False, "error": "Registro no encontrado"}, status_code=404)

    has_incoming = bool(item.incoming_path or item.downloaded_path)
    has_been_sent = bool(item.library_saved or item.jellyfin_sent or item.final_path)

    if has_incoming and not has_been_sent and not force:
        return JSONResponse(
            {
                "ok": False,
                "requires_confirmation": True,
                "message": "Aún no se ha pasado a Jellyfin. ¿Seguro que quieres eliminarlo de incoming?",
            },
            status_code=409,
        )

    delete_file_if_exists(item.incoming_path)
    delete_file_if_exists(item.downloaded_path)

    if item.cover_path:
        cover_path = Path(item.cover_path)
        try:
            if cover_path.exists() and cover_path.is_file() and str(cover_path).startswith(str(settings.CONFIG_PATH)):
                cover_path.unlink()
        except Exception:
            pass

    item.is_deleted = True
    item.deleted_at = datetime.utcnow()
    item.deleted_by_user_id = user_or_response.id
    item.incoming_path = None
    item.downloaded_path = None
    item.updated_at = datetime.utcnow()
    db.commit()

    add_action(db, "deleted", download_id=item.id, user_id=user_or_response.id)

    return {"ok": True, "deleted": download_id}


@app.get("/api/history")
def api_history(request: Request, db: Session = Depends(get_db)):
    user_or_response = require_login(request, db)

    if isinstance(user_or_response, RedirectResponse):
        return JSONResponse({"ok": False, "error": "No autenticado"}, status_code=401)

    query = (
        db.query(DownloadHistory)
        .options(joinedload(DownloadHistory.user))
        .filter(DownloadHistory.is_deleted.is_(False))
    )

    if not user_or_response.is_admin:
        query = query.filter(DownloadHistory.user_id == user_or_response.id)

    items = query.order_by(DownloadHistory.id.desc()).all()
    return [row_to_dict(item) for item in items]


# -----------------------------------------------------------------------------
# Health / favicon
# -----------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "dwSongs Docker Edition", "version": "1.5.0"}


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)
