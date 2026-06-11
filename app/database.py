from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


Base = declarative_base()


engine = create_engine(
    f"sqlite:///{settings.DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()