from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import InteractionState


class Message(BaseModel):
    """A single message in an interaction."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    character_id: str
    character_name: str
    action: str  # "talk", "emote", "leave", etc.
    content: str  # What they said or did


class InteractionSession(BaseModel):
    """Active interaction session between characters."""
    
    id: Optional[str] = Field(alias="_id", default=None)
    participants: List[str]  # Character IDs
    participant_names: List[str]  # Character names for display
    interaction_type: str  # "dialog", "fight", "romance", etc.
    messages: List[Message] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        populate_by_name = True


class StartInteractionRequest(BaseModel):
    """Request to start an interaction."""
    
    character_ids: List[str]  # 2+ character IDs
    interaction_type: str = "dialog"  # "dialog", "fight", "romance"


class InteractionActionRequest(BaseModel):
    """Request to take an action during interaction."""
    
    character_id: str
    action: str  # "talk", "leave", "continue", "fight", "flirt"
    content: str  # What they say or do

