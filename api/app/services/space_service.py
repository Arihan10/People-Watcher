from typing import List, Optional, Dict, Any
from datetime import datetime
from ..database import get_database
from .llm_service import get_llm_service
import logging

logger = logging.getLogger(__name__)


class SpaceService:
    """Service for space operations."""
    
    def __init__(self):
        self.db = get_database()
        self._llm = None
    
    @property
    def llm(self):
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm
    
    async def get_space(self, space_name: str) -> Optional[Dict[str, Any]]:
        """Get space state."""
        return await self.db.spaces.find_one({"_id": space_name.lower().replace(" ", "_")})
    
    async def update_characters_present(
        self, 
        space_name: str,
        characters: List[str]
    ) -> bool:
        """Update the list of characters present in a space."""
        space_id = space_name.lower().replace(" ", "_")
        
        result = await self.db.spaces.update_one(
            {"_id": space_id},
            {
                "$set": {
                    "characters_present": characters,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        return True
    
    async def generate_context(
        self,
        space_name: str,
        characters_present: List[str],
        available_objects: List[str]
    ) -> str:
        """Generate LLM-based space context description."""
        # Get existing space for previous activities
        space = await self.get_space(space_name)
        previous_activities = space.get("activities", []) if space else []
        
        # Generate new description
        description = await self.llm.generate_space_context(
            space_name,
            characters_present,
            available_objects,
            previous_activities
        )
        
        # Update space in database
        space_id = space_name.lower().replace(" ", "_")
        await self.db.spaces.update_one(
            {"_id": space_id},
            {
                "$set": {
                    "name": space_name,
                    "activities": [description],
                    "characters_present": characters_present,
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return description


# Global instance
_space_service: Optional[SpaceService] = None


def get_space_service() -> SpaceService:
    """Get or create the space service instance."""
    global _space_service
    if _space_service is None:
        _space_service = SpaceService()
    return _space_service
