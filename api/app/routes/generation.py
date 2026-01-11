from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate", tags=["generation"])


class GenerateRequest(BaseModel):
    """Request to generate village characters."""
    num_characters: int = 10
    house_spaces: Optional[List[str]] = None
    all_spaces: Optional[List[str]] = None


class GenerateResponse(BaseModel):
    """Response from character generation."""
    status: str
    message: str
    characters_created: Optional[int] = None
    relationships_created: Optional[int] = None
    character_names: Optional[List[str]] = None


@router.post("", response_model=GenerateResponse)
async def generate_village(request: GenerateRequest) -> GenerateResponse:
    """
    Generate village characters and relationships.
    
    This endpoint clears existing data and generates new characters
    with the specified house assignments.
    """
    try:
        # Import here to avoid circular imports
        import sys
        import os
        
        # Add parent directory to path to import generate_characters
        api_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        
        from generate_characters import generate_village as gen_village
        
        logger.info(f"Starting generation: {request.num_characters} characters")
        if request.all_spaces:
            logger.info(f"All spaces: {request.all_spaces}")
        if request.house_spaces:
            logger.info(f"House spaces: {request.house_spaces}")
        
        result = await gen_village(
            num_characters=request.num_characters,
            house_spaces=request.house_spaces,
            all_spaces=request.all_spaces
        )
        
        return GenerateResponse(
            status="ok",
            message=f"Successfully generated {result['characters_created']} characters and {result['relationships_created']} relationships",
            characters_created=result['characters_created'],
            relationships_created=result['relationships_created'],
            character_names=result['character_names']
        )
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return GenerateResponse(
            status="error",
            message=str(e)
        )
