from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import InteractionState


class InteractionSummary(BaseModel):
    """Summary of an interaction between characters."""
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_type: str  # "dialog", "fight", "romance", etc.
    summary: str  # LLM-generated summary
    emotional_impact: Optional[str] = None
    relationship_score_change: Optional[int] = None


class Relationship(BaseModel):
    """Bidirectional relationship between two characters.
    
    Single document stores both perspectives - how each feels about the other.
    Character 1 and Character 2 can have different feelings/scores.
    """
    
    id: Optional[str] = Field(alias="_id", default=None)
    
    # The two characters in this relationship
    character_id_1: str
    character_id_2: str
    
    # Character 1's perspective of Character 2
    char1_relationship_type: str = Field(default="Acquaintance")
    char1_summary: str = Field(default="")
    char1_score: int = Field(default=0, ge=-100, le=100)
    char1_interaction_history: List[InteractionSummary] = Field(default_factory=list)
    
    # Character 2's perspective of Character 1
    char2_relationship_type: str = Field(default="Acquaintance")
    char2_summary: str = Field(default="")
    char2_score: int = Field(default=0, ge=-100, le=100)
    char2_interaction_history: List[InteractionSummary] = Field(default_factory=list)
    
    # Current interaction state (shared)
    current_interaction_state: InteractionState = InteractionState.NONE
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "character_id_1": "507f1f77bcf86cd799439011",
                "character_id_2": "507f1f77bcf86cd799439012",
                "char1_relationship_type": "Romantic",
                "char1_summary": "Has a crush on her",
                "char1_score": 80,
                "char2_relationship_type": "Friendly",
                "char2_summary": "Finds him annoying but amusing",
                "char2_score": 45,
                "current_interaction_state": "none"
            }
        }
