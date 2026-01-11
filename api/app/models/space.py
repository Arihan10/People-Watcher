from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class Space(BaseModel):
    """Space state in the world."""
    id: str = Field(alias="_id")
    name: str
    activities: List[str] = Field(default_factory=list)
    characters_present: List[str] = Field(default_factory=list)
    last_updated: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
