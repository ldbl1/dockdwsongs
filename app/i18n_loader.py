import json
from pathlib import Path


I18N_DIR = Path(__file__).parent / "i18n"
DEFAULT_LANGUAGE = "es"


def get_supported_languages() -> dict:
    languages = {}

    if not I18N_DIR.exists():
        return {
            "es": "Español",
        }

    for file_path in sorted(I18N_DIR.glob("*.json")):
        language_code = file_path.stem

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            language_name = data.get("language_name", language_code)
            languages[language_code] = language_name
        except Exception:
            continue

    if not languages:
        languages["es"] = "Español"

    return languages


def load_language(language_code: str) -> dict:
    fallback = _load_json(DEFAULT_LANGUAGE)

    if not fallback:
        fallback = {
            "language_name": "Español",
            "home": "Inicio",
            "settings": "Ajustes",
        }

    if language_code == DEFAULT_LANGUAGE:
        return fallback

    selected = _load_json(language_code)

    merged = fallback.copy()
    merged.update(selected)

    return merged


def _load_json(language_code: str) -> dict:
    file_path = I18N_DIR / f"{language_code}.json"

    if not file_path.exists():
        return {}

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}