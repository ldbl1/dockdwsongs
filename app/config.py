import os
from pathlib import Path


class Settings:
    DOWNLOAD_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", "/downloads"))
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "/data/dwsongs.db"))
    CONFIG_PATH: Path = Path(os.getenv("CONFIG_PATH", "/config"))

    LIBRARY_MUSIC_PATH: Path = Path(os.getenv("LIBRARY_MUSIC_PATH", "/library/music"))

    JELLYFIN_URL: str = os.getenv("JELLYFIN_URL", "")
    JELLYFIN_API_KEY: str = os.getenv("JELLYFIN_API_KEY", "")
    AUTO_REFRESH_JELLYFIN: bool = (
        os.getenv("AUTO_REFRESH_JELLYFIN", "false").lower() == "true"
    )

    @property
    def INCOMING_PATH(self) -> Path:
        return self.DOWNLOAD_PATH / "_incoming"


settings = Settings()

settings.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
settings.INCOMING_PATH.mkdir(parents=True, exist_ok=True)
settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
settings.CONFIG_PATH.mkdir(parents=True, exist_ok=True)
settings.LIBRARY_MUSIC_PATH.mkdir(parents=True, exist_ok=True)