from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import logging

from ..database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reset", tags=["reset"])


class ResetResponse(BaseModel):
    """Response from simulation reset."""
    status: str
    message: str
    characters_reset: int = 0
    relationships_reset: int = 0


@router.post("", response_model=ResetResponse)
async def reset_simulation() -> ResetResponse:
    """
    Reset the simulation to its initial state.
    
    This clears all character history (action_log, memory_log),
    resets needs/feelings to defaults, clears interaction states,
    and clears relationship interaction history.
    
    Character profiles and relationship backgrounds are preserved.
    """
    try:
        db = get_database()
        
        # Reset all characters
        character_result = await db.characters.update_many(
            {},
            {
                "$set": {
                    "current_activity": {
                        "type": "idle",
                        "target": None,
                        "description": "idle",
                        "started_at": datetime.utcnow()
                    },
                    "needs": {
                        "happiness": 70,
                        "energy": 100,
                        "hunger": 30,
                        "hygiene": 80,
                        "health": 100
                    },
                    "feelings": {
                        "anger": 0,
                        "sadness": 0,
                        "excitement": 20,
                        "fear": 0,
                        "love": 0
                    },
                    "action_log": [],
                    "memory_log": [],
                    "is_in_interaction": False,
                    "active_session_id": None,
                    "last_known_position": None,
                    "last_known_space": None
                }
            }
        )
        
        # Reset all relationships (clear interaction history but keep backgrounds and base feelings)
        relationship_result = await db.relationships.update_many(
            {},
            {
                "$set": {
                    "interaction_history": [],
                    "is_interacting": False,
                    "active_session_id": None
                }
            }
        )
        
        # Clear any interaction sessions
        if "interaction_sessions" in await db.list_collection_names():
            await db.interaction_sessions.delete_many({})
        
        # Clear space states if they exist
        if "space_states" in await db.list_collection_names():
            await db.space_states.delete_many({})
        
        logger.info(f"Simulation reset: {character_result.matched_count} characters, {relationship_result.matched_count} relationships")
        
        return ResetResponse(
            status="ok",
            message=f"Simulation reset successfully. {character_result.matched_count} characters and {relationship_result.matched_count} relationships restored to initial state.",
            characters_reset=character_result.matched_count,
            relationships_reset=relationship_result.matched_count
        )
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        return ResetResponse(
            status="error",
            message=str(e)
        )
