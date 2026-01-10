from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class SpaceState(BaseModel):
    """Single space state from Unity."""
    
    space_name: str  # Name of the space
    description: Optional[str] = None  # What's happening there (from generate-space-context)
    characters_present: List[str] = []  # Character names in this space
    available_objects: List[str] = []  # Objects that can be interacted with


class CharacterLocation(BaseModel):
    """Location of a character in the world."""
    character_name: str
    space_name: str


class GlobalContext(BaseModel):
    """Global context - world state from Unity."""
    
    time: Optional[str] = None  # "morning", "afternoon", "evening", "night"
    all_spaces: List[str] = []  # All space names that exist in the map
    character_locations: List[CharacterLocation] = []  # Where every character is


class DecisionRequest(BaseModel):
    """Request for character to make a decision."""
    
    trigger_source: str  # What triggered this decision
    space_states: List[SpaceState] = []  # All spaces in perception radius (can be multiple)
    global_context: Optional[GlobalContext] = None


class ActionOutput(BaseModel):
    """Action for Unity to execute."""
    
    actionType: str  # "move", "initiate_conversation", "use_object", "wait", "continue"
    props: Dict[str, Any] = {}  # Action-specific properties


class DecisionResponse(BaseModel):
    """Response from decision-making."""
    
    character_name: str
    trigger_source: str
    state_changes: List[Dict[str, Any]]  # Changes to apply to character state
    action: ActionOutput  # What Unity should make the character do
    reasoning: Optional[str] = None  # Why they made this decision
    timestamp: datetime
