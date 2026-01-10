from fastapi import APIRouter, HTTPException, status
from typing import List
from bson import ObjectId
from datetime import datetime
from app.database import get_database
from app.models.interaction_session import (
    InteractionSession,
    StartInteractionRequest,
    InteractionActionRequest,
    Message
)
from app.models.enums import InteractionState
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/interaction-sessions", tags=["interaction-sessions"])


def session_helper(session) -> dict:
    """Convert MongoDB document to dict."""
    if session:
        session["_id"] = str(session["_id"])
        return session
    return None


async def ensure_relationship_exists(db, char_id_1: str, char_id_2: str, participants_data: list):
    """
    Ensure a bidirectional relationship exists between two characters.
    If not, create one automatically (first interaction).
    """
    # Check if relationship exists (either direction)
    existing = await db.relationships.find_one({
        "$or": [
            {"character_id_1": char_id_1, "character_id_2": char_id_2},
            {"character_id_1": char_id_2, "character_id_2": char_id_1}
        ]
    })
    
    if not existing:
        # Get character info
        char1 = next((c for c in participants_data if str(c["_id"]) == char_id_1), None)
        char2 = next((c for c in participants_data if str(c["_id"]) == char_id_2), None)
        
        if char1 and char2:
            # Create new bidirectional relationship with neutral defaults
            new_relationship = {
                "character_id_1": char_id_1,
                "character_id_2": char_id_2,
                
                # Char1's perspective
                "char1_relationship_type": "Acquaintance",
                "char1_summary": f"{char1['name']} has just met {char2['name']}",
                "char1_score": 0,
                "char1_interaction_history": [],
                
                # Char2's perspective
                "char2_relationship_type": "Acquaintance",
                "char2_summary": f"{char2['name']} has just met {char1['name']}",
                "char2_score": 0,
                "char2_interaction_history": [],
                
                "current_interaction_state": "none"
            }
            
            await db.relationships.insert_one(new_relationship)
            
            # Update both characters' relationship lists
            await db.characters.update_one(
                {"_id": ObjectId(char_id_1)},
                {"$addToSet": {"relationships": char_id_2}}
            )
            await db.characters.update_one(
                {"_id": ObjectId(char_id_2)},
                {"$addToSet": {"relationships": char_id_1}}
            )
            
            print(f"Auto-created bidirectional relationship: {char1['name']} <-> {char2['name']}")


@router.post("/", response_model=InteractionSession, status_code=status.HTTP_201_CREATED)
async def start_interaction(request: StartInteractionRequest):
    """Start a new interaction session between characters."""
    db = get_database()
    
    # Validate all participants exist
    if len(request.character_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 characters")
    
    participants_data = []
    for char_id in request.character_ids:
        if not ObjectId.is_valid(char_id):
            raise HTTPException(status_code=400, detail=f"Invalid character ID: {char_id}")
        
        char = await db.characters.find_one({"_id": ObjectId(char_id)})
        if not char:
            raise HTTPException(status_code=404, detail=f"Character not found: {char_id}")
        participants_data.append(char)
    
    # Check if any participant is already in an active session
    for char_id in request.character_ids:
        existing_session = await db.interaction_sessions.find_one({
            "participants": char_id,
            "is_active": True
        })
        if existing_session:
            raise HTTPException(
                status_code=400,
                detail=f"Character {char_id} is already in an active interaction"
            )
    
    # Ensure relationships exist for all participant pairs (create if first interaction)
    for i, char_id_1 in enumerate(request.character_ids):
        for char_id_2 in request.character_ids[i+1:]:
            # Check and create bidirectional relationship
            await ensure_relationship_exists(db, char_id_1, char_id_2, participants_data)
    
    # Create session
    session_data = {
        "participants": request.character_ids,  # Store as strings
        "participant_names": [char["name"] for char in participants_data],
        "interaction_type": request.interaction_type,
        "messages": [],
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "is_active": True
    }
    
    print(f"Creating conversation session: {participants_data[0]['name']} & {participants_data[1]['name']}")
    print(f"Participant IDs: {request.character_ids}")
    
    result = await db.interaction_sessions.insert_one(session_data)
    
    # Update character relationship states to show they're interacting
    for char_id in request.character_ids:
        await db.characters.update_one(
            {"_id": ObjectId(char_id)},
            {"$set": {"is_interacting": True}}
        )
    
    # Update relationships to set interaction state
    for i, char_id_1 in enumerate(request.character_ids):
        for char_id_2 in request.character_ids[i+1:]:
            # Update bidirectional relationship
            await db.relationships.update_one(
                {
                    "$or": [
                        {"character_id_1": char_id_1, "character_id_2": char_id_2},
                        {"character_id_1": char_id_2, "character_id_2": char_id_1}
                    ]
                },
                {"$set": {"current_interaction_state": request.interaction_type}}
            )
    
    new_session = await db.interaction_sessions.find_one({"_id": result.inserted_id})
    return session_helper(new_session)


@router.get("/{session_id}", response_model=InteractionSession)
async def get_session(session_id: str):
    """Get a specific interaction session."""
    db = get_database()
    
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_helper(session)


@router.post("/{session_id}/end", response_model=InteractionSession)
async def end_session(session_id: str):
    """Manually end an interaction session."""
    db = get_database()
    
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    await end_interaction(session_id, db)
    
    session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
    return session_helper(session)


@router.post("/{session_id}/advance", response_model=InteractionSession)
async def advance_conversation(session_id: str):
    """
    AI-generated: Advance the conversation by having the current character speak.
    Uses LLM to generate realistic dialogue based on full context.
    """
    db = get_database()
    
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.get("is_active"):
        print(f"Warning: Session {session_id} is not active")
        raise HTTPException(status_code=400, detail="Session is not active")
    
    # Get current character
    current_char_id = session["current_turn"]
    current_char = await db.characters.find_one({"_id": ObjectId(current_char_id)})
    if not current_char:
        raise HTTPException(status_code=404, detail="Current character not found")
    
    # Get other participants
    other_participants = []
    for char_id in session["participants"]:
        if char_id != current_char_id:
            char = await db.characters.find_one({"_id": ObjectId(char_id)})
            if char:
                other_participants.append(char)
    
    # Get relationships with other participants (bidirectional format)
    relationships = []
    for other_char in other_participants:
        other_id = str(other_char["_id"])
        rel = await db.relationships.find_one({
            "$or": [
                {"character_id_1": current_char_id, "character_id_2": other_id},
                {"character_id_1": other_id, "character_id_2": current_char_id}
            ]
        })
        if rel:
            relationships.append(rel)
    
    # Get space info if characters are in a space
    space_info = None
    # For now, we could look up space by checking which space has these characters
    # Or Unity would tell us. For prototype, we'll skip this.
    
    # Generate dialogue using LLM
    llm = get_llm_service()
    
    try:
        dialogue = await llm.generate_dialogue(
            character=current_char,
            other_characters=other_participants,
            conversation_history=session.get("messages", []),
            space_info=space_info,
            relationships=relationships
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
    
    # Create message
    message = Message(
        character_id=current_char_id,
        character_name=current_char["name"],
        action="talk",
        content=dialogue
    )
    
    # Add message to session
    await db.interaction_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"messages": message.model_dump()}}
    )
    
    # Add to character's action log with full context
    other_names = [name for name in session.get('participant_names', []) if name != current_char['name']]
    await db.characters.update_one(
        {"_id": ObjectId(current_char_id)},
        {"$push": {"action_log": {
            "timestamp": datetime.utcnow(),
            "action": f"spoke to {', '.join(other_names)}",
            "details": f"Said: \"{dialogue}\""
        }}}
    )
    
    # Switch turn to next participant
    current_idx = session["participants"].index(current_char_id)
    next_idx = (current_idx + 1) % len(session["participants"])
    next_turn = session["participants"][next_idx]
    
    await db.interaction_sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {"current_turn": next_turn}}
    )
    
    # Get updated session
    updated_session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
    return session_helper(updated_session)


async def end_interaction(session_id: str, db):
    """Helper function to end an interaction."""
    session = await db.interaction_sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        return
    
    print(f"Ending conversation session: {session.get('participant_names', [])}")
    
    # Update characters - no longer interacting
    for char_id in session["participants"]:
        await db.characters.update_one(
            {"_id": ObjectId(char_id)},
            {"$set": {"is_interacting": False}}
        )
    
    # Reset relationship interaction states
    for i in range(len(session["participants"])):
        for j in range(i + 1, len(session["participants"])):
            char_id_1 = session["participants"][i]
            char_id_2 = session["participants"][j]
            
            await db.relationships.update_one(
                {
                    "$or": [
                        {"character_id_1": char_id_1, "character_id_2": char_id_2},
                        {"character_id_1": char_id_2, "character_id_2": char_id_1}
                    ]
                },
                    {"$set": {"current_interaction_state": "none"}}
                )
    
    # Delete the session from database
    await db.interaction_sessions.delete_one({"_id": ObjectId(session_id)})
    print(f"Session deleted from database")
    
    # Generate LLM summary with per-character feelings and relationship changes
    if session.get("messages"):
        # Get participant characters
        participants = []
        for char_id in session["participants"]:
            char = await db.characters.find_one({"_id": ObjectId(char_id)})
            if char:
                participants.append(char)
        
        # Generate summary using LLM
        llm = get_llm_service()
        try:
            summary_data = await llm.generate_interaction_summary(
                participants=participants,
                messages=session["messages"],
                interaction_type=session["interaction_type"]
            )
            
            overall_summary = summary_data["summary"]
            emotional_impacts = summary_data.get("emotional_impacts", {})
            relationship_changes = summary_data.get("relationship_changes", {})
            
            print(f"Generated summary: {overall_summary}")
            print(f"Emotional impacts: {emotional_impacts}")
            print(f"Relationship changes: {relationship_changes}")
        except Exception as e:
            print(f"Failed to generate LLM summary: {e}")
            overall_summary = f"Had a {session['interaction_type']} with {len(session['messages'])} exchanges"
            emotional_impacts = {}
            relationship_changes = {}
        
        # Build character name to ID mapping
        name_to_id = {char["name"]: str(char["_id"]) for char in participants}
        
        # Update relationships for all participant pairs (bidirectional)
        for i in range(len(session["participants"])):
            for j in range(i + 1, len(session["participants"])):
                char_id_1 = session["participants"][i]
                char_id_2 = session["participants"][j]
                char_1 = participants[i]
                char_2 = participants[j]
                
                # Get relationship changes for both directions
                change_1to2 = relationship_changes.get(f"{char_1['name']} -> {char_2['name']}", 0)
                change_2to1 = relationship_changes.get(f"{char_2['name']} -> {char_1['name']}", 0)
                
                # Get emotional impacts
                char_1_feeling = emotional_impacts.get(char_1['name'], 'neutral')
                char_2_feeling = emotional_impacts.get(char_2['name'], 'neutral')
                
                # Create interaction summaries
                summary_1 = {
                    "timestamp": datetime.utcnow(),
                    "action_type": session["interaction_type"],
                    "summary": overall_summary,
                    "emotional_impact": char_1_feeling,
                    "relationship_score_change": change_1to2
                }
                
                summary_2 = {
                    "timestamp": datetime.utcnow(),
                    "action_type": session["interaction_type"],
                    "summary": overall_summary,
                    "emotional_impact": char_2_feeling,
                    "relationship_score_change": change_2to1
                }
                
                # Update the bidirectional relationship
                update_result = await db.relationships.update_one(
                    {
                        "$or": [
                            {"character_id_1": char_id_1, "character_id_2": char_id_2},
                            {"character_id_1": char_id_2, "character_id_2": char_id_1}
                        ]
                    },
                    {
                        "$push": {
                            "char1_interaction_history": summary_1,
                            "char2_interaction_history": summary_2
                        },
                        "$inc": {
                            "char1_score": change_1to2,
                            "char2_score": change_2to1
                        }
                    }
                )
                
                if update_result.modified_count > 0:
                    print(f"Updated {char_1['name']} <-> {char_2['name']}: {change_1to2:+d}/{change_2to1:+d}")
        
        # Ensure all scores stay within bounds (-100 to 100)
        await db.relationships.update_many(
            {"char1_score": {"$gt": 100}},
            {"$set": {"char1_score": 100}}
        )
        await db.relationships.update_many(
            {"char1_score": {"$lt": -100}},
            {"$set": {"char1_score": -100}}
        )
        await db.relationships.update_many(
            {"char2_score": {"$gt": 100}},
            {"$set": {"char2_score": 100}}
        )
        await db.relationships.update_many(
            {"char2_score": {"$lt": -100}},
            {"$set": {"char2_score": -100}}
        )
        
        # Add to each character's memory log
        for char_id, char in zip(session["participants"], participants):
            char_feeling = emotional_impacts.get(char['name'], 'neutral')
            other_names = [p['name'] for p in participants if str(p['_id']) != char_id]
            
            memory_entry = {
                "timestamp": datetime.utcnow(),
                "event": f"Had a {session['interaction_type']} with {', '.join(other_names)}. {overall_summary}",
                "emotional_impact": char_feeling
            }
            
            await db.characters.update_one(
                {"_id": ObjectId(char_id)},
                {"$push": {"memory_log": memory_entry}}
            )

