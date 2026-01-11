from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class SessionType(str, Enum):
    """Types of interaction sessions."""
    DIALOG = "dialog"
    FIGHT = "fight"
    ROMANCE = "romance"


class InteractionTurn(BaseModel):
    """A single turn in an interaction."""
    character: str
    action_type: str
    content: str
    emotional_impact: Optional[Dict[str, Dict[str, int]]] = None
    timestamp: datetime


class InteractionSession(BaseModel):
    """Active or completed interaction session."""
    id: str = Field(alias="_id")
    participants: List[str]  # Character IDs
    session_type: SessionType
    is_active: bool = True
    started_at: datetime
    
    # Turn management
    current_turn: str  # Character ID whose turn it is
    turn_count: int = 0
    last_action_at: Optional[datetime] = None
    
    # Full conversation history
    turns: List[InteractionTurn] = Field(default_factory=list)
    
    # Snapshot of context when session started
    context_snapshot: Dict = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
