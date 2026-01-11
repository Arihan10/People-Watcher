from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class Appearance(BaseModel):
    """Character appearance configuration."""
    top: int = Field(ge=0, le=5)
    bottom: int = Field(ge=0, le=5)
    shoes: int = Field(ge=0, le=3)
    hair: int = Field(ge=0, le=7)


class ActivityType(str, Enum):
    """Character activity types."""
    IDLE = "idle"
    MOVING = "moving"
    USE_OBJECT = "use_object"
    IN_INTERACTION = "in_interaction"


class CurrentActivity(BaseModel):
    """Current character activity."""
    type: ActivityType
    target: Optional[str] = None
    description: Optional[str] = None
    started_at: datetime


class Needs(BaseModel):
    """Character needs (0-100)."""
    happiness: int = Field(ge=0, le=100, default=70)
    energy: int = Field(ge=0, le=100, default=100)
    hunger: int = Field(ge=0, le=100, default=30)
    hygiene: int = Field(ge=0, le=100, default=80)
    health: int = Field(ge=0, le=100, default=100)


class Feelings(BaseModel):
    """Character feelings (0-100)."""
    anger: int = Field(ge=0, le=100, default=0)
    sadness: int = Field(ge=0, le=100, default=0)
    excitement: int = Field(ge=0, le=100, default=20)
    fear: int = Field(ge=0, le=100, default=0)
    love: int = Field(ge=0, le=100, default=0)


class ActionLogEntry(BaseModel):
    """Entry in character's action log."""
    t: datetime
    action: str


class MemoryLogEntry(BaseModel):
    """Entry in character's memory log."""
    t: datetime
    observation: str


class Position(BaseModel):
    """Character position in world."""
    x: float
    z: float


class Character(BaseModel):
    """Complete character model."""
    id: str = Field(alias="_id")
    name: str
    age: int = Field(ge=18, le=80)
    gender: str
    race: str
    occupation: str
    
    # Appearance
    appearance: Appearance
    
    # Personality (static)
    personality_traits: List[str]
    core_motivations: List[str]
    ambition_level: int = Field(ge=0, le=100)
    confrontational_tendency: int = Field(ge=0, le=100)
    background: str
    
    # Dynamic state
    current_desire: str
    current_activity: CurrentActivity
    needs: Needs
    feelings: Feelings
    
    # Logs (capped at 20)
    action_log: List[ActionLogEntry] = Field(default_factory=list)
    memory_log: List[MemoryLogEntry] = Field(default_factory=list)
    
    # Concurrency control
    is_in_interaction: bool = False
    active_session_id: Optional[str] = None
    
    # Position
    last_known_position: Optional[Position] = None
    last_known_space: Optional[str] = None
    
    # Home location
    home_space: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
