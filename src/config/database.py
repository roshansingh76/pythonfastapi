from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session,sessionmaker
from src.config.settings import settings
engine =create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10
)

SessionLocal =sessionmaker(

    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()