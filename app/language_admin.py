from pathlib import Path
from typing import List
import json
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.i18n_loader import get_supported_languages, load_language


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

I18N_DIR = Path("app/i18n")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,8}([_-][a-zA-Z0-9]{2,8})?$")


def _safe_language_code(language_code: str) -> str:
    language_code = (language_code or "").strip().lower()

    if not LANGUAGE_CODE_PATTERN.match(language_code):
        return "es"

    return language_code


def _language_file(language_code: str) -> Path:
    return I18N_DIR / f"{_safe_language_code(language_code)}.json"


def _load_language_raw(language_code: str) -> dict:
    language_code = _safe_language_code(language_code)
    path = _language_file(language_code)

    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_language_raw(language_code: str, data: dict) -> None:
    language_code = _safe_language_code(language_code)
    I18N_DIR.mkdir(parents=True, exist_ok=True)
    path = _language_file(language_code)
    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _all_language_keys(selected_data: dict) -> list[str]:
    base_data = _load_language_raw("es")
    keys = set(base_data.keys()) | set(selected_data.keys())
    return sorted(keys)


def _editor_context(
    request: Request,
    db: Session,
    selected_language: str,
    message: str = "",
    error: str = "",
) -> dict:
    selected_language = _safe_language_code(selected_language)
    selected_data = _load_language_raw(selected_language)
    base_data = _load_language_raw("es")
    keys = _all_language_keys(selected_data)

    rows = []
    for key in keys:
        rows.append(
            {
                "key": key,
                "base_value": base_data.get(key, ""),
                "value": selected_data.get(key, ""),
                "missing": key not in selected_data,
            }
        )

    current_user = get_current_user(request, db)

    return {
        "request": request,
        "current_user": current_user,
        "t": load_language("es"),
        "config": {},
        "jellyfin_configured": False,
        "languages": get_supported_languages(),
        "selected_language": selected_language,
        "rows": rows,
        "message": message,
        "error": error,
    }


@router.get("/settings/languages", response_class=HTMLResponse)
def language_editor_page(
    request: Request,
    language: str = "es",
    message: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    return templates.TemplateResponse(
        request=request,
        name="language_editor.html",
        context=_editor_context(
            request=request,
            db=db,
            selected_language=language,
            message=message,
            error=error,
        ),
    )


@router.post("/settings/languages/save")
def save_language_editor(
    request: Request,
    language: str = Form("es"),
    keys: List[str] = Form([]),
    values: List[str] = Form([]),
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    language = _safe_language_code(language)

    if len(keys) != len(values):
        return RedirectResponse(
            f"/settings/languages?language={language}&error=Formulario inválido",
            status_code=303,
        )

    data = {}
    for key, value in zip(keys, values):
        clean_key = (key or "").strip()
        if clean_key:
            data[clean_key] = value

    if "language_name" not in data or not str(data.get("language_name", "")).strip():
        data["language_name"] = language

    _save_language_raw(language, data)

    return RedirectResponse(
        f"/settings/languages?language={language}&message=Idioma guardado correctamente",
        status_code=303,
    )


@router.post("/settings/languages/create")
def create_language(
    request: Request,
    new_language: str = Form(""),
    base_language: str = Form("es"),
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    new_language = _safe_language_code(new_language)
    base_language = _safe_language_code(base_language)

    if not new_language or new_language == "es" and (new_language_file := _language_file(new_language)).exists():
        return RedirectResponse(
            "/settings/languages?error=El código de idioma no es válido o ya existe",
            status_code=303,
        )

    new_language_file = _language_file(new_language)

    if new_language_file.exists():
        return RedirectResponse(
            f"/settings/languages?language={new_language}&error=El idioma ya existe",
            status_code=303,
        )

    base_data = _load_language_raw(base_language) or _load_language_raw("es")
    data = dict(base_data)
    data["language_name"] = new_language
    _save_language_raw(new_language, data)

    return RedirectResponse(
        f"/settings/languages?language={new_language}&message=Idioma creado correctamente",
        status_code=303,
    )


@router.post("/settings/languages/add-key")
def add_language_key(
    request: Request,
    language: str = Form("es"),
    new_key: str = Form(""),
    new_value: str = Form(""),
    db: Session = Depends(get_db),
):
    admin_or_response = require_admin(request, db)

    if isinstance(admin_or_response, RedirectResponse):
        return admin_or_response

    language = _safe_language_code(language)
    new_key = (new_key or "").strip()

    if not new_key:
        return RedirectResponse(
            f"/settings/languages?language={language}&error=La clave no puede estar vacía",
            status_code=303,
        )

    data = _load_language_raw(language)

    if new_key in data:
        return RedirectResponse(
            f"/settings/languages?language={language}&error=La clave ya existe",
            status_code=303,
        )

    data[new_key] = new_value
    _save_language_raw(language, data)

    return RedirectResponse(
        f"/settings/languages?language={language}&message=Clave añadida correctamente",
        status_code=303,
    )
