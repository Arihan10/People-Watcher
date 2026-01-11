from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    """All valid action types."""
    MOVE = "move"
    USE_OBJECT = "use_object"
    SPEAK = "speak"
    INITIATE_INTERACTION = "initiate_interaction"
    SPEAK_IN_INTERACTION = "speak_in_interaction"
    FIGHT_ACTION = "fight_action"
    ROMANCE_ACTION = "romance_action"
    LEAVE_INTERACTION = "leave_interaction"
    NONE = "none"


class SpaceState(BaseModel):
    """State of a space for decision context."""
    space_name: str
    description: str
    characters_present: List[str]
    available_objects: List[str]


class CharacterLocation(BaseModel):
    """Character location for global context."""
    character_name: str
    space_name: Optional[str] = None


class GlobalContext(BaseModel):
    """Global world context."""
    time: str
    all_spaces: List[str]
    character_locations: List[CharacterLocation]


class DecideRequest(BaseModel):
    """Request for character decision."""
    trigger_source: str
    priority: int = 1  # 0=Low, 1=Normal, 2=High, 3=Critical
    session_id: Optional[str] = None
    space_states: List[SpaceState]
    global_context: GlobalContext


class Action(BaseModel):
    """Action to be performed."""
    actionType: ActionType
    props: Dict[str, Any] = Field(default_factory=dict)


class DecideResponse(BaseModel):
    """Response from decision endpoint."""
    status: str = "ok"
    inner_thought: Optional[str] = None
    state_changes: Optional[Dict[str, Any]] = None
    action: Action
    session_id: Optional[str] = None
    next_turn: Optional[str] = None
    reason: Optional[str] = None


class ActivityUpdateRequest(BaseModel):
    """Request to update character activity."""
    activity_type: str  # arrived, started_using, stopped_using, idle
    target: Optional[str] = None
    description: str


class ActivityUpdateResponse(BaseModel):
    """Response from activity update."""
    status: str = "ok"
    current_activity: Dict[str, Any]


class SpaceContextRequest(BaseModel):
    """Request to generate space context."""
    space_name: str
    characters_present: List[str]
    available_objects: List[str]


class SpaceContextResponse(BaseModel):
    """Response with generated space context."""
    space_name: str
    description: str
