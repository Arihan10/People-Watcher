from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from bson import ObjectId
from app.database import get_database
from app.services.llm_service import get_llm_service
from pydantic import BaseModel

router = APIRouter(prefix="/context", tags=["context"])


class SpaceContextRequest(BaseModel):
    """Request to generate space context description."""
    
    space_name: str
    characters_present: List[str]  # Full names of characters
    available_objects: List[str] = []  # Objects in this space (Unity provides)
    description: Optional[str] = None  # Previous description to update minimally


class SpaceContextResponse(BaseModel):
    """Response with generated space description."""
    
    space_name: str
    description: str


@router.post("/generate-space-context", response_model=SpaceContextResponse)
async def generate_space_context(request: SpaceContextRequest):
    """
    Generate AI description of what's happening in a space.
    
    Unity sends space name + list of character names.
    Backend looks up characters, gets their desires/actions, generates description.
    """
    db = get_database()
    
    # Look up characters by full name
    characters_in_space = []
    for char_name in request.characters_present:
        # Try exact match first
        char = await db.characters.find_one({"name": char_name})
        if char:
            characters_in_space.append(char)
        else:
            # Try case-insensitive match
            char = await db.characters.find_one({"name": {"$regex": f"^{char_name}$", "$options": "i"}})
            if char:
                characters_in_space.append(char)
            else:
                print(f"Warning: Character '{char_name}' not found in database")
    
    if len(characters_in_space) == 0:
        # No characters present
        return SpaceContextResponse(
            space_name=request.space_name,
            description=f"{request.space_name} is quiet and empty."
        )
    
    # Generate description using LLM
    llm = get_llm_service()
    
    try:
        description = await llm.generate_space_context_from_characters(
            space_name=request.space_name,
            characters=characters_in_space,
            available_objects=request.available_objects,
            current_description=request.description
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
    
    return SpaceContextResponse(
        space_name=request.space_name,
        description=description
    )

