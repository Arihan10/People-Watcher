from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from bson import ObjectId
from app.database import get_database
from app.models.relationship import Relationship

router = APIRouter(prefix="/relationships", tags=["relationships"])


def relationship_helper(relationship) -> dict:
    """Convert MongoDB document to dict."""
    if relationship:
        relationship["_id"] = str(relationship["_id"])
        return relationship
    return None


@router.get("/character/{character_id}")
async def get_character_relationships(character_id: str):
    """Get all relationships for a character with their perspective extracted.
    
    Returns relationships where character is involved, with 'my_perspective' field
    showing how they feel about the other person.
    """
    db = get_database()
    
    if not ObjectId.is_valid(character_id):
        raise HTTPException(status_code=400, detail="Invalid character ID format")
    
    # Check if character exists
    character = await db.characters.find_one({"_id": ObjectId(character_id)})
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    relationships = []
    async for relationship in db.relationships.find({
        "$or": [
            {"character_id_1": character_id},
            {"character_id_2": character_id}
        ]
    }):
        rel_dict = relationship_helper(relationship)
        
        # Extract this character's perspective
        if rel_dict["character_id_1"] == character_id:
            # This character is char1
            rel_dict["my_perspective"] = {
                "other_character_id": rel_dict["character_id_2"],
                "relationship_type": rel_dict["char1_relationship_type"],
                "summary": rel_dict["char1_summary"],
                "score": rel_dict["char1_score"],
                "interaction_history": rel_dict["char1_interaction_history"]
            }
            rel_dict["their_perspective"] = {
                "relationship_type": rel_dict["char2_relationship_type"],
                "summary": rel_dict["char2_summary"],
                "score": rel_dict["char2_score"]
            }
        else:
            # This character is char2
            rel_dict["my_perspective"] = {
                "other_character_id": rel_dict["character_id_1"],
                "relationship_type": rel_dict["char2_relationship_type"],
                "summary": rel_dict["char2_summary"],
                "score": rel_dict["char2_score"],
                "interaction_history": rel_dict["char2_interaction_history"]
            }
            rel_dict["their_perspective"] = {
                "relationship_type": rel_dict["char1_relationship_type"],
                "summary": rel_dict["char1_summary"],
                "score": rel_dict["char1_score"]
            }
        
        relationships.append(rel_dict)
    
    return relationships
