from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict
from datetime import datetime

class GameRecordSchema(BaseModel):
    # Enable SQLAlchemy ORM compat and strict types
    model_config = ConfigDict(from_attributes=True, extra='ignore')

    id: Optional[int] = None
    source_file: str = Field(..., max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=512)
    status: str = Field(default="extracted", max_length=50)
    extracted_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
