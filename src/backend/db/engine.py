"""Database engine and session configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.backend.config import settings
from src.backend.db.models import Base, configure_timescale

engine = create_engine(settings.db_url, echo=settings.debug)
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database objects for local development."""
    Base.metadata.create_all(bind=engine)
    configure_timescale(engine)
