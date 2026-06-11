from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database import Base


class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, index=True)

    url = Column(Text, nullable=False)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)

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

    audio_format = Column(String, default="mp3")
    downloaded_path = Column(Text, nullable=True)
    final_path = Column(Text, nullable=True)
    cover_path = Column(Text, nullable=True)

    jellyfin_sent = Column(Boolean, default=False)
    duplicate = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)