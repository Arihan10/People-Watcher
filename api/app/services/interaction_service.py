from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from ..database import get_database
from .llm_service import get_llm_service
from .relationship_service import get_relationship_service
import logging

logger = logging.getLogger(__name__)


class InteractionService:
    """Service for interaction session management."""
    
    def __init__(self):
        self.db = get_database()
        self._llm = None
        self._relationship_service = None
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm
    
    @property
    def relationship_service(self):
        if self._relationship_service is None:
            self._relationship_service = get_relationship_service()
        return self._relationship_service
    
    async def create_session_atomic(
        self,
        initiator_id: str,
        target_id: str,
        session_type: str,
        context_snapshot: Dict[str, Any]
    ) -> Optional[str]:
        """
        Atomically create an interaction session.
        Returns session_id if successful, None if target unavailable.
        """
        # First check both characters exist
        target_char = await self.db.characters.find_one({"_id": target_id})
        if not target_char:
            logger.error(f"Target character {target_id} does not exist in database!")
            return None
        
        # Try to atomically lock both characters
        result = await self.db.characters.update_many(
            {
                "_id": {"$in": [initiator_id, target_id]},
                "is_in_interaction": False  # Only if BOTH are free
            },
            {"$set": {"is_in_interaction": True}}
        )
        
        if result.modified_count != 2:
            # Race lost - one or both already claimed
            # Rollback any partial update
            await self.db.characters.update_many(
                {"_id": {"$in": [initiator_id, target_id]}},
                {"$set": {"is_in_interaction": False}}
            )
            logger.warning(f"Failed to lock both characters for session: {initiator_id}, {target_id} (modified: {result.modified_count})")
            return None
        
        # Won the race - create session
        session_id = str(uuid.uuid4())
        session = {
            "_id": session_id,
            "participants": [initiator_id, target_id],
            "session_type": session_type,
            "is_active": True,
            "started_at": datetime.utcnow(),
            "current_turn": target_id,  # Target goes first after initiator's opening
            "turn_count": 0,
            "last_action_at": datetime.utcnow(),
            "turns": [],
            "context_snapshot": context_snapshot
        }
        
        await self.db.interaction_sessions.insert_one(session)
        
        # Update relationship to mark as interacting
        await self.relationship_service.set_interacting(
            initiator_id, target_id, True, session_id
        )
        
        # Also update characters with session_id
        await self.db.characters.update_many(
            {"_id": {"$in": [initiator_id, target_id]}},
            {"$set": {"active_session_id": session_id}}
        )
        
        logger.info(f"Created session {session_id} between {initiator_id} and {target_id}")
        return session_id
    
    async def get_active_session(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character's active session if any."""
        return await self.db.interaction_sessions.find_one({
            "participants": character_id,
            "is_active": True
        })
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        return await self.db.interaction_sessions.find_one({"_id": session_id})
    
    async def add_turn(
        self,
        session_id: str,
        character_id: str,
        action_type: str,
        content: str,
        emotional_impact: Optional[Dict] = None
    ) -> bool:
        """Add a turn to the session."""
        turn = {
            "character": character_id,
            "action_type": action_type,
            "content": content,
            "emotional_impact": emotional_impact,
            "timestamp": datetime.utcnow()
        }
        
        result = await self.db.interaction_sessions.update_one(
            {"_id": session_id},
            {
                "$push": {"turns": turn},
                "$inc": {"turn_count": 1},
                "$set": {"last_action_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    async def update_current_turn(self, session_id: str, next_character_id: str) -> bool:
        """Update whose turn it is."""
        result = await self.db.interaction_sessions.update_one(
            {"_id": session_id},
            {"$set": {"current_turn": next_character_id}}
        )
        return result.modified_count > 0
    
    async def end_session(
        self,
        session_id: str,
        reason: str = "completed"
    ) -> Optional[str]:
        """
        End an interaction session.
        Returns the summary text.
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        # Generate summary
        summary = await self.llm.summarize_interaction(session)
        
        # Mark session as inactive
        await self.db.interaction_sessions.update_one(
            {"_id": session_id},
            {"$set": {"is_active": False}}
        )
        
        # Unlock both characters
        participants = session.get("participants", [])
        await self.db.characters.update_many(
            {"_id": {"$in": participants}},
            {
                "$set": {
                    "is_in_interaction": False,
                    "active_session_id": None
                }
            }
        )
        
        # Update relationship
        if len(participants) == 2:
            char_a, char_b = participants[0], participants[1]
            
            # Add summary to relationship history
            await self.relationship_service.add_interaction_summary(
                char_a, char_b, summary
            )
            
            # Mark relationship as not interacting
            await self.relationship_service.set_interacting(
                char_a, char_b, False, None
            )
        
        logger.info(f"Ended session {session_id}: {reason}")
        return summary
    
    async def is_locked(self, character_id: str) -> bool:
        """Check if a character is locked in an interaction."""
        character = await self.db.characters.find_one(
            {"_id": character_id},
            {"is_in_interaction": 1}
        )
        return character.get("is_in_interaction", False) if character else False


# Global instance
_interaction_service: Optional[InteractionService] = None


def get_interaction_service() -> InteractionService:
    """Get or create the interaction service instance."""
    global _interaction_service
    if _interaction_service is None:
        _interaction_service = InteractionService()
    return _interaction_service
