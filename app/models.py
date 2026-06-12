from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    downloads = relationship("DownloadHistory", back_populates="user", cascade="save-update")
    actions = relationship("DownloadAction", back_populates="user", cascade="save-update")


class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    url = Column(Text, nullable=False)
    original_title = Column(String, nullable=True)
    uploader = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    thumbnail_url = Column(Text, nullable=True)

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
    incoming_path = Column(Text, nullable=True)
    downloaded_path = Column(Text, nullable=True)
    final_path = Column(Text, nullable=True)
    cover_path = Column(Text, nullable=True)

    incoming_size_bytes = Column(Integer, nullable=True)
    final_size_bytes = Column(Integer, nullable=True)

    jellyfin_sent = Column(Boolean, default=False)
    library_saved = Column(Boolean, default=False)
    duplicate = Column(Boolean, default=False)

    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_user_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    queued_at = Column(DateTime, nullable=True)
    info_fetched_at = Column(DateTime, nullable=True)
    download_started_at = Column(DateTime, nullable=True)
    downloaded_at = Column(DateTime, nullable=True)
    metadata_updated_at = Column(DateTime, nullable=True)
    moved_to_library_at = Column(DateTime, nullable=True)
    jellyfin_refreshed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="downloads")
    actions = relationship("DownloadAction", back_populates="download", cascade="all, delete-orphan")


class DownloadAction(Base):
    __tablename__ = "download_actions"

    id = Column(Integer, primary_key=True, index=True)
    download_id = Column(Integer, ForeignKey("download_history.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    download = relationship("DownloadHistory", back_populates="actions")
    user = relationship("User", back_populates="actions")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)

    user = relationship("User")
