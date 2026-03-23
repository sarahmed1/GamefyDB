from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime, timezone
from src.database.session import Base

class GameRecord(Base):
    __tablename__ = "game_records"

    id = Column(Integer, primary_key=True, index=True)
    source_file = Column(String(255), index=True, nullable=False)
    title = Column(String(255), index=True, nullable=True)
    url = Column(String(512), nullable=True)
    status = Column(String(50), default="extracted")
    extracted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_data = Column(JSON, nullable=True)
