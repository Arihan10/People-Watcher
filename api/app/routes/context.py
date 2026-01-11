from fastapi import APIRouter
import logging

from ..models import SpaceContextRequest, SpaceContextResponse
from ..services.space_service import get_space_service
from ..logger_middleware import get_session_logger

logger = logging.getLogger(__name__)
session_logger = get_session_logger()
router = APIRouter(prefix="/context", tags=["context"])


@router.post("/generate-space-context")
async def generate_space_context(request: SpaceContextRequest) -> SpaceContextResponse:
    """Generate LLM-based description for a space."""
    session_logger.log("SPACE CONTEXT", f"Generating context for {request.space_name}", {
        "characters": request.characters_present,
        "objects": request.available_objects
    })
    
    space_service = get_space_service()
    
    description = await space_service.generate_context(
        request.space_name,
        request.characters_present,
        request.available_objects
    )
    
    session_logger.log("SPACE DESCRIPTION", f"{request.space_name}: {description}")
    
    return SpaceContextResponse(
        space_name=request.space_name,
        description=description
    )
