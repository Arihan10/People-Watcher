from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class RelationshipStatus(str, Enum):
    """Relationship status types."""
    FRIENDLY = "friendly"
    ROMANTIC = "romantic"
    ANTAGONISTIC = "antagonistic"
    NEUTRAL = "neutral"


class RelationshipDirection(BaseModel):
    """One direction of a relationship (A's feelings toward B)."""
    status: RelationshipStatus
    affection: int = Field(ge=0, le=100)
    trust: int = Field(ge=0, le=100)
    respect: int = Field(ge=0, le=100)


class InteractionHistoryEntry(BaseModel):
    """A summary of a past interaction."""
    timestamp: datetime
    summary: str
    relationship_delta: Optional[dict] = None


class Relationship(BaseModel):
    """Relationship between two characters (bidirectional)."""
    id: str = Field(alias="_id")
    characters: List[str]  # Sorted alphabetically
    
    # Directional feelings (using character IDs as keys in dict)
    # e.g., "timmy_to_marlene": {...}
    # This will be stored as dynamic fields in MongoDB
    
    background: str
    interaction_history: List[InteractionHistoryEntry] = Field(default_factory=list)
    
    # Current state
    is_interacting: bool = False
    active_session_id: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def get_relationship_id(char1: str, char2: str) -> str:
    """Generate relationship ID from two character IDs (alphabetically sorted)."""
    return "_".join(sorted([char1, char2]))


def get_direction_key(source: str, target: str) -> str:
    """Get the key for directional feelings (source_to_target)."""
    return f"{source}_to_{target}"
