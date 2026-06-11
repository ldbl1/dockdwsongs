import os
from pathlib import Path


class Settings:
    DOWNLOAD_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", "/downloads"))
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "/data/dwsongs.db"))
    CONFIG_PATH: Path = Path(os.getenv("CONFIG_PATH", "/config"))

    JELLYFIN_URL: str = os.getenv("JELLYFIN_URL", "")
    JELLYFIN_API_KEY: str = os.getenv("JELLYFIN_API_KEY", "")
    AUTO_REFRESH_JELLYFIN: bool = os.getenv("AUTO_REFRESH_JELLYFIN", "true").lower() == "true"


settings = Settings()

settings.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
settings.CONFIG_PATH.mkdir(parents=True, exist_ok=True)
