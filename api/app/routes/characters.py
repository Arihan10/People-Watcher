from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.routes.interaction_sessions import end_interaction as end_conversation_helper
from app.models.character import (
    Character,
    CharacterCreate,
    CharacterUpdate,
    DesireUpdate,
    ActionLogEntry,
    MemoryLogEntry,
    Needs,
    Position
)
from app.models.decision import (
    DecisionRequest,
    DecisionResponse,
    SpaceState,
    GlobalContext,
    ActionOutput
)
from app.services.llm_service import get_llm_service
from pydantic import BaseModel

router = APIRouter(prefix="/characters", tags=["characters"])


def character_helper(character) -> dict:
    """Convert MongoDB document to dict."""
    if character:
        character["_id"] = str(character["_id"])
        return character
    return None


@router.get("/", response_model=List[Character])
async def list_characters():
    """List all characters."""
    db = get_database()
    characters = []
    
    async for character in db.characters.find():
        characters.append(character_helper(character))
    
    return characters


@router.get("/{character_id}", response_model=Character)
async def get_character(character_id: str):
    """Get a specific character by ID."""
    db = get_database()
    
    if not ObjectId.is_valid(character_id):
        raise HTTPException(status_code=400, detail="Invalid character ID format")
    
    character = await db.characters.find_one({"_id": ObjectId(character_id)})
    
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return character_helper(character)


class ObjectUseResponse(BaseModel):
    """Response from using an object."""
    character_name: str
    object_name: str
    flavor_text: str
    timestamp: datetime


@router.post("/{character_id}/use/{object_name}", response_model=ObjectUseResponse)
async def use_object(character_id: str, object_name: str):
    """
    Character interacts with an object.
    LLM generates contextual emoji flavor text based on character personality and object.
    
    Note: No space_id needed - Unity manages all spatial data.
    """
    db = get_database()
    
    if not ObjectId.is_valid(character_id):
        raise HTTPException(status_code=400, detail="Invalid character ID format")
    
    # Get character
    character = await db.characters.find_one({"_id": ObjectId(character_id)})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Generate flavor text using LLM (no space info needed)
    llm = get_llm_service()
    
    try:
        flavor_text = await llm.generate_object_interaction(
            character=character,
            object_name=object_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
    
    # Add to action log
    timestamp = datetime.utcnow()
    action_entry = {
        "timestamp": timestamp,
        "action": "use_object",
        "details": f"Used {object_name}: {flavor_text}"
    }
    
    await db.characters.update_one(
        {"_id": ObjectId(character_id)},
        {"$push": {"action_log": action_entry}}
    )
    
    # Return response
    return ObjectUseResponse(
        character_name=character["name"],
        object_name=object_name,
        flavor_text=flavor_text,
        timestamp=timestamp
    )


from app.models.interaction_session import StartInteractionRequest
from app.routes.interaction_sessions import start_interaction

@router.post("/{character_id}/decide", response_model=DecisionResponse)
async def decide(character_id: str, request: DecisionRequest):
    """
    .decide() - AI-powered character decision making for Unity.
    
    Handles ALL decisions including:
    - Regular actions (move, talk, use object)
    - Conversation continuation (if in active conversation)
    - Leaving conversations
    
    Character evaluates their context (can perceive multiple spaces) and decides what action to take.
    Returns both state changes AND an action for Unity to execute.
    """
    db = get_database()
    
    if not ObjectId.is_valid(character_id):
        raise HTTPException(status_code=400, detail="Invalid character ID format")
    
    # Get character
    character = await db.characters.find_one({"_id": ObjectId(character_id)})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Check if character is in an active conversation
    active_session = await db.interaction_sessions.find_one({
        "participants": character_id,
        "is_active": True
    })
    
    # Collect all nearby characters from ALL visible spaces (perception radius)
    nearby_characters = []
    all_nearby_char_names = set()
    
    for space_state in request.space_states:
        all_nearby_char_names.update(space_state.characters_present)
    
    # Look up character data for all nearby people
    for char_name in all_nearby_char_names:
        if char_name != character['name']:  # Exclude self
            char = await db.characters.find_one({"name": char_name})
            if char:
                nearby_characters.append(char)
            else:
                print(f"Warning: Could not find character by name: '{char_name}'")
    
    # Get character's relationships (bidirectional)
    relationships = []
    async for rel in db.relationships.find({
        "$or": [
            {"character_id_1": character_id},
            {"character_id_2": character_id}
        ]
    }):
        relationships.append(rel)
    
    # Generate decision using LLM
    llm = get_llm_service()
    
    try:
        decision_result = await llm.generate_decision_for_unity(
            character=character,
            trigger_source=request.trigger_source,
            space_states=request.space_states,
            global_context=request.global_context,
            relationships=relationships,
            nearby_characters=nearby_characters,
            active_conversation=active_session  # Pass conversation context if in one
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
    
    # Apply state changes
    state_changes = decision_result["state_changes"]
    update_data = {}
    
    for change in state_changes:
        for key, value in change.items():
            # Map keys to database fields
            if key == "current_desire" or key == "currentDesire":
                update_data["current_desire"] = value
            elif key in ["happiness", "energy", "hunger", "hygiene", "anger", "sadness"]:
                # Convert to int if it's a string
                try:
                    int_value = int(value) if isinstance(value, str) else value
                    update_data[f"needs.{key}"] = max(0, min(100, int_value))
                except (ValueError, TypeError):
                    # Skip invalid values
                    continue
            elif key.startswith("needs."):
                # Direct needs update
                need_key = key.replace("needs.", "")
                if need_key in ["happiness", "energy", "hunger", "hygiene", "anger", "sadness"]:
                    try:
                        int_value = int(value) if isinstance(value, str) else value
                        update_data[key] = max(0, min(100, int_value))
                    except (ValueError, TypeError):
                        # Skip invalid values
                        continue
    
    # Update character in database
    if update_data:
        await db.characters.update_one(
            {"_id": ObjectId(character_id)},
            {"$set": update_data}
        )
    
    # Add decision to action log with detailed information
    action_obj = decision_result.get("action", {"actionType": "continue", "props": {}})
    action_type = action_obj.get('actionType', 'none')
    props = action_obj.get('props', {})
    reasoning = decision_result.get('reasoning', '')
    
    # Create descriptive action string
    action_description = action_type
    # Track if we handled the action internally (to avoid double-processing)
    action_handled = False

    if action_type == "move":
        destination = props.get('destination', 'unknown')
        destination_type = props.get('destination_type', 'unknown')
        action_description = f"move to {destination} ({destination_type})"
        action_handled = True  # Move is handled here (memory log below)
        
    elif action_type == "initiate_conversation":
        target = props.get('target_character', 'unknown')
        interaction_type = props.get('interaction_type', 'dialog')
        action_description = f"initiate {interaction_type} with {target}"
        
        # AUTOMATICALLY START CONVERSATION INTERNALLY
        print(f"🤖 Handling initiate_conversation internally for {character['name']} -> {target}")
        
        # Look up target character
        # Try exact match first
        target_char = await db.characters.find_one({"name": target})
        if not target_char:
            # Try case-insensitive
            target_char = await db.characters.find_one({"name": {"$regex": f"^{target}$", "$options": "i"}})
            
        if target_char:
            target_id = str(target_char["_id"])
            
            try:
                # Start the session
                session_request = StartInteractionRequest(
                    character_ids=[character_id, target_id],
                    interaction_type=interaction_type
                )
                
                # Create session (this also handles relationship creation)
                session_result = await start_interaction(session_request)
                session_id = session_result["_id"]
                
                print(f"✅ Auto-started session {session_id}")
                
                # NOW GENERATE FIRST MESSAGE IMMEDIATELY
                
                # Get active session
                active_session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
                
                # Generate first message using conversation logic
                decision_result_convo = await llm.generate_decision_for_unity(
                    character=character,
                    trigger_source="started conversation",
                    space_states=request.space_states,
                    global_context=request.global_context,
                    relationships=relationships,
                    nearby_characters=nearby_characters,
                    active_conversation=active_session
                )
                
                # Extract the speak action
                convo_action = decision_result_convo.get("action", {})
                
                if convo_action.get("actionType") in ["speak_in_conversation", "fight_in_conversation", "romance_in_conversation"]:
                    print(f"🗣️ Replacing initiate with {convo_action.get('actionType')}")
                    
                    # Update the action object to return THIS instead of initiate_conversation
                    action_obj = convo_action
                    
                    # Add the message to the session
                    if convo_action.get("actionType") == "speak_in_conversation":
                        dialogue = convo_action.get("props", {}).get("dialogue", "")
                        message = {
                            "timestamp": datetime.utcnow(),
                            "character_id": character_id,
                            "character_name": character["name"],
                            "action": "talk",
                            "content": dialogue
                        }
                    elif convo_action.get("actionType") == "fight_in_conversation":
                        action_name = convo_action.get("props", {}).get("action", "attack")
                        message = {
                            "timestamp": datetime.utcnow(),
                            "character_id": character_id,
                            "character_name": character["name"],
                            "action": "fight",
                            "content": action_name
                        }
                    elif convo_action.get("actionType") == "romance_in_conversation":
                        action_name = convo_action.get("props", {}).get("action", "romance")
                        message = {
                            "timestamp": datetime.utcnow(),
                            "character_id": character_id,
                            "character_name": character["name"],
                            "action": "romance",
                            "content": action_name
                        }
                    
                    await db.interaction_sessions.update_one(
                        {"_id": ObjectId(session_id)},
                        {"$push": {"messages": message}}
                    )
                    
                    # Force update action_type local var for correct logging/logic
                    action_type = convo_action.get("actionType")
                    
                    # IMPORTANT: Mark as handled so we don't add it again below
                    action_handled = True
                    
                else:
                    # Fallback logic...
                    print(f"❌ AI returned {convo_action.get('actionType')} instead of speak/fight/romance. Forcing speak.")
                    action_obj = {
                        "actionType": "speak_in_conversation",
                        "props": {"dialogue": f"Hello {target}."}
                    }
                    action_type = "speak_in_conversation"
                    
                    message = {
                        "timestamp": datetime.utcnow(),
                        "character_id": character_id,
                        "character_name": character["name"],
                        "action": "talk",
                        "content": f"Hello {target}."
                    }
                    await db.interaction_sessions.update_one(
                        {"_id": ObjectId(session_id)},
                        {"$push": {"messages": message}}
                    )
                    action_handled = True
                    
            except Exception as e:
                print(f"❌ Failed to auto-start conversation: {e}")
                import traceback
                traceback.print_exc()
                # Fallback if critical failure
                action_obj = {
                    "actionType": "wait",
                    "props": {}
                }
                action_handled = True
        else:
            print(f"❌ Target character '{target}' not found in DB")
            action_obj = {
                "actionType": "wait",
                "props": {}
            }
            action_handled = True
            
    elif action_type == "use_object":
        object_name = props.get('object_name', 'unknown')
        action_description = f"use_object {object_name}"
    
    # Create detailed log entry
    await db.characters.update_one(
        {"_id": ObjectId(character_id)},
        {"$push": {"action_log": {
            "timestamp": datetime.utcnow(),
            "action": action_description,
            "details": f"AI Decision: {reasoning}"
        }}}
    )
    
    # Add memory log entry when moving to a space (to remember what they saw)
    if action_type == "move":
        destination = props.get('destination', '')
        
        # Find the space description for the destination
        space_description = None
        for space_state in request.space_states:
            # Check if destination matches space name or if it's an object/person in the space
            if space_state.space_name.lower() == destination.lower():
                space_description = space_state.description
                break
            # Also check if destination is a character or object in this space
            elif (destination in space_state.characters_present or 
                  destination in space_state.available_objects):
                space_description = space_state.description
                break
        
        # Add memory of entering/approaching the space
        if space_description:
            memory_event = f"Moved to {destination}. Observed: {space_description}"
        else:
            memory_event = f"Moved to {destination}"
        
        await db.characters.update_one(
            {"_id": ObjectId(character_id)},
            {"$push": {"memory_log": {
                "timestamp": datetime.utcnow(),
                "event": memory_event,
                "emotional_impact": "neutral"
            }}}
        )
    
    # Handle conversation actions (ONLY if not already handled above)
    if active_session and not action_handled:
        action_type = action_obj.get("actionType")
        
        if action_type == "speak_in_conversation":
            # Dialogue - add talk message
            dialogue = action_obj.get("props", {}).get("dialogue", "")
            if dialogue:
                message = {
                    "timestamp": datetime.utcnow(),
                    "character_id": character_id,
                    "character_name": character["name"],
                    "action": "talk",
                    "content": dialogue
                }
                
                await db.interaction_sessions.update_one(
                    {"_id": ObjectId(active_session["_id"])},
                    {"$push": {"messages": message}}
                )
                
                print(f"💬 {character['name']} spoke in conversation.")
        
        elif action_type == "fight_in_conversation":
            # Physical confrontation - add fight message
            fight_action = action_obj.get("props", {}).get("action", "attacks")
            message = {
                "timestamp": datetime.utcnow(),
                "character_id": character_id,
                "character_name": character["name"],
                "action": "fight",
                "content": fight_action
            }
            
            await db.interaction_sessions.update_one(
                {"_id": ObjectId(active_session["_id"])},
                {"$push": {"messages": message}}
            )
            
            print(f"👊 {character['name']} used {fight_action} in fight.")
        
        elif action_type == "romance_in_conversation":
            # Romantic action - add romance message
            romance_action = action_obj.get("props", {}).get("action", "romantic_gesture")
            message = {
                "timestamp": datetime.utcnow(),
                "character_id": character_id,
                "character_name": character["name"],
                "action": "romance",
                "content": romance_action
            }
            
            await db.interaction_sessions.update_one(
                {"_id": ObjectId(active_session["_id"])},
                {"$push": {"messages": message}}
            )
            
            print(f"💕 {character['name']} performed {romance_action}.")
        
        elif action_type == "leave_conversation":
            # Explicitly leaving - end conversation
            await end_conversation_helper(active_session["_id"], db)
        
        else:
            # Any other action (move, use_object, wait) while in conversation = implicit leave
            print(f"{character['name']} chose {action_type} while in conversation - ending conversation")
            await end_conversation_helper(active_session["_id"], db)
    
    return DecisionResponse(
        character_name=character["name"],
        trigger_source=request.trigger_source,
        state_changes=state_changes,
        action=ActionOutput(**action_obj),
        reasoning=decision_result.get("reasoning"),
        timestamp=datetime.utcnow()
    )


class CharacterPosition(BaseModel):
    """Schema for a character's position."""
    character_id: str
    position: Position


class SaveAllPositionsRequest(BaseModel):
    """Schema for saving all character positions (called by Unity on shutdown)."""
    positions: List[CharacterPosition]


class SaveAllPositionsResponse(BaseModel):
    """Response from saving all character positions."""
    updated_count: int
    failed_count: int
    message: str


@router.post("/save-positions", response_model=SaveAllPositionsResponse)
async def save_all_positions(request: SaveAllPositionsRequest):
    """
    Save positions for all characters.
    Unity calls this endpoint when shutting down to persist character positions.
    
    This allows Unity to manage all positions during runtime and only save them
    when necessary (shutdown, checkpoint, etc.).
    """
    db = get_database()
    updated_count = 0
    failed_count = 0
    
    for char_pos in request.positions:
        try:
            # Validate character ID
            if not ObjectId.is_valid(char_pos.character_id):
                print(f"Warning: Invalid character ID format: {char_pos.character_id}")
                failed_count += 1
                continue
            
            # Update character position
            result = await db.characters.update_one(
                {"_id": ObjectId(char_pos.character_id)},
                {"$set": {
                    "position.x": char_pos.position.x,
                    "position.y": char_pos.position.y
                }}
            )
            
            if result.modified_count > 0:
                updated_count += 1
            else:
                # Character might not exist or position didn't change
                character_exists = await db.characters.find_one({"_id": ObjectId(char_pos.character_id)})
                if not character_exists:
                    print(f"Warning: Character not found: {char_pos.character_id}")
                    failed_count += 1
                else:
                    # Position didn't change, still count as success
                    updated_count += 1
                    
        except Exception as e:
            print(f"Error updating position for character {char_pos.character_id}: {str(e)}")
            failed_count += 1
    
    total = updated_count + failed_count
    
    return SaveAllPositionsResponse(
        updated_count=updated_count,
        failed_count=failed_count,
        message=f"Updated {updated_count}/{total} character positions successfully"
    )

