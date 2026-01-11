from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
import logging

from ..models import (
    DecideRequest, DecideResponse, Action, ActionType,
    ActivityUpdateRequest, ActivityUpdateResponse
)
from ..services.character_service import get_character_service
from ..services.relationship_service import get_relationship_service
from ..services.interaction_service import get_interaction_service
from ..services.llm_service import get_llm_service
from ..logger_middleware import get_session_logger

logger = logging.getLogger(__name__)
session_logger = get_session_logger()
router = APIRouter(prefix="/characters", tags=["characters"])


def name_to_id(name: str) -> str:
    """Convert character display name to ID format.
    
    LLM and Unity use display names like "Lily Park" but database stores
    character IDs like "lily_park". This function converts between formats.
    """
    return name.lower().replace(" ", "_")


@router.get("")
async def get_characters() -> List[Dict[str, Any]]:
    """Get all characters for Unity spawning."""
    # Start new logging session when Unity connects
    session_logger.start_new_session()
    session_logger.log("UNITY CONNECTED", "Unity requested character list - Starting new session")
    
    character_service = get_character_service()
    characters = await character_service.get_all()
    
    session_logger.log("CHARACTERS LOADED", f"Loaded {len(characters)} characters", {
        "character_names": [c.get('name') for c in characters]
    })
    
    return characters


@router.get("/{character_id}")
async def get_character(character_id: str) -> Dict[str, Any]:
    """Get a single character by ID."""
    character_service = get_character_service()
    character = await character_service.get_by_id(character_id)
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character


@router.post("/{character_id}/decide")
async def decide(character_id: str, request: DecideRequest) -> DecideResponse:
    """
    Core decision endpoint. Handles both normal decisions and interaction turns.
    """
    # Log the decision request
    session_logger.log_decision(character_id, request.trigger_source, request.priority)
    
    character_service = get_character_service()
    relationship_service = get_relationship_service()
    interaction_service = get_interaction_service()
    llm_service = get_llm_service()
    
    # Get character
    character = await character_service.get_by_id(character_id)
    if not character:
        session_logger.log_error("NOT_FOUND", f"Character {character_id} not found")
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Check for active session
    active_session = await interaction_service.get_active_session(character_id)
    
    # Handle interrupts (Critical priority while in interaction)
    if active_session and request.priority >= 3:  # Critical
        # For now, always interrupt on critical
        # Could add LLM-based should_interrupt check here
        logger.info(f"Interrupting session {active_session['_id']} for critical trigger")
        session_logger.log_interaction("INTERRUPTED", active_session['_id'], 
                                     active_session.get('participants', []),
                                     {"reason": "critical trigger", "trigger": request.trigger_source})
        await interaction_service.end_session(
            active_session["_id"],
            reason="interrupted"
        )
        active_session = None
    
    # INTERACTION MODE
    if active_session:
        session_logger.log("MODE", f"{character_id} processing in INTERACTION mode", {
            "session_id": active_session['_id'],
            "session_type": active_session.get('session_type')
        })
        response = await _process_interaction_turn(
            character, active_session, request, 
            character_service, interaction_service, llm_service
        )
        session_logger.log_action(character_id, response.action.actionType.value, response.action.props)
        return response
    
    # NORMAL MODE
    session_logger.log("MODE", f"{character_id} processing in NORMAL mode")
    response = await _process_normal_decision(
        character, request,
        character_service, relationship_service, interaction_service, llm_service
    )
    session_logger.log_action(character_id, response.action.actionType.value, response.action.props)
    return response


async def _process_interaction_turn(
    character: Dict,
    session: Dict,
    request: DecideRequest,
    character_service,
    interaction_service,
    llm_service
) -> DecideResponse:
    session_logger.log("INTERACTION TURN", f"Processing turn for {character['_id']} in session {session['_id'][:8]}...")
    """Process a turn within an interaction."""
    
    # Get nearby relationships (for context building)
    # Unity sends display names (e.g., "Lily Park") but we need IDs (e.g., "lily_park")
    relationship_service = get_relationship_service()
    nearby_char_names = []
    for space in request.space_states:
        nearby_char_names.extend(space.characters_present)
    nearby_char_ids = list(set([name_to_id(c) for c in nearby_char_names if name_to_id(c) != character["_id"]]))
    
    nearby_relationships = await relationship_service.get_relationships_for_nearby(
        character["_id"], nearby_char_ids
    )
    
    # Get LLM decision
    llm_response = await llm_service.decide(
        character,
        request.trigger_source,
        [s.model_dump() for s in request.space_states],
        request.global_context.model_dump(),
        nearby_relationships,
        is_in_interaction=True,
        interaction_context=session
    )
    
    # Apply state changes
    if llm_response.get("state_changes"):
        await character_service.update_state(character["_id"], llm_response["state_changes"])
    
    action = llm_response["action"]
    action_type = action["actionType"]
    
    # Add turn to session
    content = action.get("props", {}).get("dialogue", "") or action.get("props", {}).get("action", "")
    await interaction_service.add_turn(
        session["_id"],
        character["_id"],
        action_type,
        content
    )
    
    # Handle leave
    if action_type == "leave_interaction":
        session_logger.log_interaction("ENDING", session["_id"], session.get("participants", []),
                                     {"reason": "left", "by": character["_id"]})
        summary = await interaction_service.end_session(session["_id"], reason="left")
        
        return DecideResponse(
            status="ok",
            inner_thought=llm_response.get("inner_thought"),
            state_changes=llm_response.get("state_changes"),
            action=Action(**action),
            session_id=session["_id"]
        )
    
    # Continue interaction - update turn and return with next_turn
    participants = session.get("participants", [])
    next_char = [p for p in participants if p != character["_id"]][0]
    
    await interaction_service.update_current_turn(session["_id"], next_char)
    
    return DecideResponse(
        status="ok",
        inner_thought=llm_response.get("inner_thought"),
        state_changes=llm_response.get("state_changes"),
        action=Action(**action),
        session_id=session["_id"],
        next_turn=next_char
    )


async def _process_normal_decision(
    character: Dict,
    request: DecideRequest,
    character_service,
    relationship_service,
    interaction_service,
    llm_service
) -> DecideResponse:
    """Process a normal (non-interaction) decision."""
    
    # Get nearby relationships for context
    # Unity sends display names (e.g., "Lily Park") but we need IDs (e.g., "lily_park")
    nearby_char_names = []
    for space in request.space_states:
        nearby_char_names.extend(space.characters_present)
    nearby_char_ids = list(set([name_to_id(c) for c in nearby_char_names if name_to_id(c) != character["_id"]]))
    
    nearby_relationships = await relationship_service.get_relationships_for_nearby(
        character["_id"], nearby_char_ids
    )
    
    # Get LLM decision
    llm_response = await llm_service.decide(
        character,
        request.trigger_source,
        [s.model_dump() for s in request.space_states],
        request.global_context.model_dump(),
        nearby_relationships,
        is_in_interaction=False,
        interaction_context=None
    )
    
    # Apply state changes
    if llm_response.get("state_changes"):
        session_logger.log_state_change(character["_id"], llm_response["state_changes"])
        await character_service.update_state(character["_id"], llm_response["state_changes"])
    
    action = llm_response["action"]
    action_type = action["actionType"]
    
    # Log action
    action_desc = f"{action_type}"
    if action_type == "move":
        action_desc += f" to {action.get('props', {}).get('destination', 'unknown')}"
    elif action_type == "use_object":
        action_desc += f" with {action.get('props', {}).get('object_name', 'unknown')}"
    elif action_type == "initiate_interaction":
        action_desc += f" with {action.get('props', {}).get('target_character', 'unknown')}"
    
    session_logger.log("ACTION LOGGED", f"{character['_id']}: {action_desc}")
    await character_service.add_action_log(character["_id"], action_desc)
    
    # Handle initiate_interaction
    if action_type == "initiate_interaction":
        target_character_name = action["props"].get("target_character")
        interaction_type = action["props"].get("type", "dialog")
        
        if not target_character_name:
            logger.error("initiate_interaction missing target_character")
            return DecideResponse(
                status="ok",
                action=Action(actionType=ActionType.NONE, props={})
            )
        
        # Convert display name to character ID format
        # LLM outputs names like "Lily Park" but database stores IDs like "lily_park"
        target_character_id = name_to_id(target_character_name)
        
        # Create context snapshot
        context_snapshot = {
            "space": request.space_states[0].space_name if request.space_states else "unknown",
            "time": request.global_context.time,
            "nearby_characters": nearby_char_ids
        }
        
        # Try to create session atomically
        session_id = await interaction_service.create_session_atomic(
            character["_id"],
            target_character_id,
            interaction_type,
            context_snapshot
        )
        
        if session_id is None:
            # Target was unavailable
            session_logger.log("INTERACTION BLOCKED", 
                f"{character['_id']} → {target_character_id}: target unavailable or already in interaction")
            return DecideResponse(
                status="target_unavailable",
                reason=f"{target_character_name} is already in an interaction",
                action=Action(actionType=ActionType.NONE, props={})
            )
        
        # Success - log the session creation with next_turn info
        session_logger.log_interaction("STARTED", session_id, 
            [character["_id"], target_character_id],
            {"type": interaction_type, "next_turn": target_character_id})
        
        # Success - return with session info
        # next_turn uses ID format for consistency (Unity's FindCharacter handles both)
        return DecideResponse(
            status="ok",
            inner_thought=llm_response.get("inner_thought"),
            state_changes=llm_response.get("state_changes"),
            action=Action(**action),
            session_id=session_id,
            next_turn=target_character_id
        )
    
    # Normal action
    return DecideResponse(
        status="ok",
        inner_thought=llm_response.get("inner_thought"),
        state_changes=llm_response.get("state_changes"),
        action=Action(**action)
    )


@router.post("/{character_id}/activity")
async def update_activity(
    character_id: str,
    request: ActivityUpdateRequest
) -> ActivityUpdateResponse:
    """Update character's current activity."""
    session_logger.log("ACTIVITY UPDATE", f"{character_id}: {request.activity_type}", {
        "target": request.target,
        "description": request.description
    })
    
    character_service = get_character_service()
    
    # Update activity in database
    activity = await character_service.update_activity(
        character_id,
        request.activity_type,
        request.target,
        request.description
    )
    
    return ActivityUpdateResponse(
        status="ok",
        current_activity=activity
    )
