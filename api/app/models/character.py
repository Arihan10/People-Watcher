from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class Appearance(BaseModel):
    """Character appearance using asset codes."""
    
    hair: int = Field(ge=0, le=15)  # 0-15: hair styles
    shoes: int = Field(ge=0, le=6)  # 0-6: shoe types
    bottom: int = Field(ge=0, le=5)  # 0-5: bottom clothing
    top: int = Field(ge=0, le=10)   # 0-10: top clothing


class PyObjectId(ObjectId):
    """Custom type for handling MongoDB ObjectId in Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info=None):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        schema.update(type="string")
        return schema


class ActionLogEntry(BaseModel):
    """A single action log entry with timestamp."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str
    details: Optional[str] = None


class MemoryLogEntry(BaseModel):
    """A significant event or observation from space contexts."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event: str
    space_id: Optional[str] = None
    emotional_impact: Optional[str] = None


class Position(BaseModel):
    """Character position in Unity world space."""
    
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class Needs(BaseModel):
    """Character needs on 0-100 scales."""
    
    happiness: int = Field(default=50, ge=0, le=100)
    energy: int = Field(default=50, ge=0, le=100)
    hunger: int = Field(default=50, ge=0, le=100)
    hygiene: int = Field(default=50, ge=0, le=100)
    anger: int = Field(default=50, ge=0, le=100)
    sadness: int = Field(default=50, ge=0, le=100)


class Character(BaseModel):
    """Character model representing a character in the simulation."""
    
    id: Optional[str] = Field(alias="_id", default=None)
    
    # Profile (static/semi-static data)
    name: str
    age: int
    appearance: Appearance  # Asset-based appearance
    race: str
    gender: str
    occupation: str
    background: str
    
    # Personality traits (array of strings)
    personality_traits: List[str] = Field(default_factory=list)
    # Example: ["ambitious", "creative", "introverted", "optimistic"]
    
    # Needs/Status
    needs: Needs = Field(default_factory=Needs)
    
    # Position (Unity world space - managed by Unity, saved here on shutdown)
    position: Position = Field(default_factory=Position)
    
    # Current state
    current_desire: Optional[str] = None
    
    # Logs
    action_log: List[ActionLogEntry] = Field(default_factory=list)
    memory_log: List[MemoryLogEntry] = Field(default_factory=list)
    
    # Relationships (adjacency list - stores IDs of related characters)
    relationships: List[str] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Sarah Chen",
                "age": 28,
                "appearance": {
                    "hair": 12,  # bun
                    "shoes": 1,  # orange running shoes
                    "bottom": 3, # jeans
                    "top": 8     # green hoodie
                },
                "race": "Asian",
                "gender": "Female",
                "occupation": "Software Engineer",
                "background": "Grew up in a small town, moved to the city for college. Passionate about AI and gaming.",
                "personality_traits": ["ambitious", "creative", "driven", "friendly"],
                "needs": {
                    "happiness": 70,
                    "energy": 60,
                    "hunger": 40,
                    "hygiene": 80,
                    "anger": 20,
                    "sadness": 30
                },
                "current_desire": "Wants to grab coffee with a friend"
            }
        }


class CharacterCreate(BaseModel):
    """Schema for creating a new character."""
    
    name: str
    age: int
    appearance: Appearance
    race: str
    gender: str
    occupation: str
    background: str
    personality_traits: List[str] = Field(default_factory=list)
    needs: Optional[Needs] = None
    current_desire: Optional[str] = None


class CharacterUpdate(BaseModel):
    """Schema for updating a character's state."""
    
    personality_traits: Optional[List[str]] = None
    needs: Optional[Needs] = None
    position: Optional[Position] = None
    current_desire: Optional[str] = None


class DesireUpdate(BaseModel):
    """Schema for updating a character's current desire."""
    
    current_desire: str

