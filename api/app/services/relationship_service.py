from typing import List, Optional, Dict, Any
from datetime import datetime
from ..database import get_database
from ..models.relationship import get_relationship_id, get_direction_key
import logging

logger = logging.getLogger(__name__)


class RelationshipService:
    """Service for relationship operations."""
    
    def __init__(self):
        self.db = get_database()
    
    async def get_relationship(self, char_a: str, char_b: str) -> Optional[Dict[str, Any]]:
        """Get relationship between two characters."""
        rel_id = get_relationship_id(char_a, char_b)
        return await self.db.relationships.find_one({"_id": rel_id})
    
    async def get_relationships_for(self, character_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a character."""
        cursor = self.db.relationships.find({"characters": character_id})
        relationships = await cursor.to_list(length=None)
        return relationships
    
    async def get_relationships_for_nearby(
        self, 
        character_id: str, 
        nearby_character_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get relationships for a character with nearby characters."""
        if not nearby_character_ids:
            return []
        
        # Find relationships where character_id is in the pair AND one of nearby is too
        cursor = self.db.relationships.find({
            "characters": {
                "$all": [character_id],
                "$in": nearby_character_ids
            }
        })
        relationships = await cursor.to_list(length=None)
        return relationships
    
    async def update_relationship(
        self, 
        char_a: str, 
        char_b: str, 
        changes: Dict[str, Any]
    ) -> bool:
        """Update relationship fields."""
        rel_id = get_relationship_id(char_a, char_b)
        
        result = await self.db.relationships.update_one(
            {"_id": rel_id},
            {"$set": changes}
        )
        return result.modified_count > 0
    
    async def set_interacting(
        self, 
        char_a: str, 
        char_b: str, 
        is_interacting: bool,
        session_id: Optional[str] = None
    ) -> bool:
        """Set interaction state for a relationship."""
        rel_id = get_relationship_id(char_a, char_b)
        
        result = await self.db.relationships.update_one(
            {"_id": rel_id},
            {
                "$set": {
                    "is_interacting": is_interacting,
                    "active_session_id": session_id
                }
            }
        )
        return result.modified_count > 0
    
    async def add_interaction_summary(
        self,
        char_a: str,
        char_b: str,
        summary: str,
        relationship_delta: Optional[Dict] = None
    ) -> bool:
        """Add interaction summary to relationship history."""
        rel_id = get_relationship_id(char_a, char_b)
        
        history_entry = {
            "timestamp": datetime.utcnow(),
            "summary": summary,
            "relationship_delta": relationship_delta
        }
        
        result = await self.db.relationships.update_one(
            {"_id": rel_id},
            {
                "$push": {
                    "interaction_history": {
                        "$each": [history_entry],
                        "$slice": -50  # Keep last 50 interactions
                    }
                }
            }
        )
        return result.modified_count > 0


# Global instance
_relationship_service: Optional[RelationshipService] = None


def get_relationship_service() -> RelationshipService:
    """Get or create the relationship service instance."""
    global _relationship_service
    if _relationship_service is None:
        _relationship_service = RelationshipService()
    return _relationship_service
