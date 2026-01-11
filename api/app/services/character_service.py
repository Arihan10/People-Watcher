from typing import List, Optional, Dict, Any
from datetime import datetime
from ..database import get_database
import logging

logger = logging.getLogger(__name__)


class CharacterService:
    """Service for character operations."""
    
    def __init__(self):
        self.db = get_database()
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """Get all characters."""
        cursor = self.db.characters.find({})
        characters = await cursor.to_list(length=None)
        return characters
    
    async def get_by_id(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a single character by ID."""
        return await self.db.characters.find_one({"_id": character_id})
    
    async def update_state(self, character_id: str, state_changes: Dict[str, Any]) -> bool:
        """Update character state (needs, feelings, desire, activity, etc.)."""
        update_doc = {}
        
        # Handle current_desire
        if "current_desire" in state_changes:
            update_doc["current_desire"] = state_changes["current_desire"]
        
        # Handle current_activity (LLM provides a narrative description string)
        if "current_activity" in state_changes and state_changes["current_activity"]:
            activity_desc = state_changes["current_activity"]
            update_doc["current_activity"] = {
                "type": "active",
                "target": None,
                "description": activity_desc,
                "started_at": datetime.utcnow()
            }
        
        # Handle feelings (merge with existing)
        if "feelings" in state_changes:
            for feeling, value in state_changes["feelings"].items():
                update_doc[f"feelings.{feeling}"] = max(0, min(100, value))
        
        # Handle needs (merge with existing, can be negative for decrements)
        if "needs" in state_changes:
            for need, value in state_changes["needs"].items():
                # Get current value first
                char = await self.get_by_id(character_id)
                if char:
                    current = char.get("needs", {}).get(need, 50)
                    new_value = max(0, min(100, current + value))
                    update_doc[f"needs.{need}"] = new_value
        
        # Handle add_memory
        if "add_memory" in state_changes and state_changes["add_memory"]:
            memory_entry = {
                "t": datetime.utcnow(),
                "observation": state_changes["add_memory"]
            }
            # Push to memory_log, keep only last 20
            await self.db.characters.update_one(
                {"_id": character_id},
                {
                    "$push": {
                        "memory_log": {
                            "$each": [memory_entry],
                            "$slice": -20
                        }
                    }
                }
            )
        
        # Apply updates
        if update_doc:
            result = await self.db.characters.update_one(
                {"_id": character_id},
                {"$set": update_doc}
            )
            return result.modified_count > 0
        
        return True
    
    async def add_action_log(self, character_id: str, action: str) -> bool:
        """Add entry to character's action log."""
        action_entry = {
            "t": datetime.utcnow(),
            "action": action
        }
        
        result = await self.db.characters.update_one(
            {"_id": character_id},
            {
                "$push": {
                    "action_log": {
                        "$each": [action_entry],
                        "$slice": -20
                    }
                }
            }
        )
        return result.modified_count > 0
    
    async def add_memory_log(self, character_id: str, observation: str) -> bool:
        """Add entry to character's memory log."""
        memory_entry = {
            "t": datetime.utcnow(),
            "observation": observation
        }
        
        result = await self.db.characters.update_one(
            {"_id": character_id},
            {
                "$push": {
                    "memory_log": {
                        "$each": [memory_entry],
                        "$slice": -20
                    }
                }
            }
        )
        return result.modified_count > 0
    
    async def update_activity(
        self, 
        character_id: str,
        activity_type: str,
        target: Optional[str],
        description: str
    ) -> Dict[str, Any]:
        """Update character's current activity."""
        activity = {
            "type": activity_type,
            "target": target,
            "description": description,
            "started_at": datetime.utcnow()
        }
        
        await self.db.characters.update_one(
            {"_id": character_id},
            {"$set": {"current_activity": activity}}
        )
        
        return activity
    
    async def get_decision_context(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get complete context for a character's decision."""
        character = await self.get_by_id(character_id)
        if not character:
            return None
        
        return character


# Global instance
_character_service: Optional[CharacterService] = None


def get_character_service() -> CharacterService:
    """Get or create the character service instance."""
    global _character_service
    if _character_service is None:
        _character_service = CharacterService()
    return _character_service
