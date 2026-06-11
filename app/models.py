from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, index=True)

    # YouTube / origen
    url = Column(Text, nullable=False)
    original_title = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    thumbnail_url = Column(Text, nullable=True)

    # Estado
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)

    # Metadatos editables
    title = Column(String, nullable=True)
    artist = Column(String, nullable=True)
    album_artist = Column(String, nullable=True)
    album = Column(String, nullable=True)
    year = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    track_number = Column(String, nullable=True)
    disc_number = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    lyrics = Column(Text, nullable=True)

    # Formato / rutas
    audio_format = Column(String, default="mp3")

    # Fichero descargado temporalmente en /downloads/_incoming
    incoming_path = Column(Text, nullable=True)

    # Alias compatible por si algún código viejo aún usa downloaded_path
    downloaded_path = Column(Text, nullable=True)

    # Fichero final organizado en /library/music
    final_path = Column(Text, nullable=True)

    # Carátula, si más adelante la usamos
    cover_path = Column(Text, nullable=True)

    # Jellyfin / biblioteca
    jellyfin_sent = Column(Boolean, default=False)
    library_saved = Column(Boolean, default=False)
    duplicate = Column(Boolean, default=False)

    # Fechas
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)