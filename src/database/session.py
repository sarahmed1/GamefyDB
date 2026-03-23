from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

DEFAULT_DB_URL = "sqlite:///local.db"

def init_db(db_url: str = DEFAULT_DB_URL):
    """Initializes the database by creating tables if they don't exist."""
    engine = create_engine(db_url, echo=False)
    # Import models here to ensure they are registered with Base before create_all
    import src.database.models  # noqa
    Base.metadata.create_all(engine)
    return engine

def get_session(db_url: str = DEFAULT_DB_URL):
    """Yields a database session."""
    engine = create_engine(db_url, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
