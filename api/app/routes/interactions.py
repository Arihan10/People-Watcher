from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging

from ..services.interaction_service import get_interaction_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/active/{character_id}")
async def get_active_session(character_id: str) -> Optional[Dict[str, Any]]:
    """Get character's active interaction session."""
    interaction_service = get_interaction_service()
    session = await interaction_service.get_active_session(character_id)
    return session


@router.post("/{session_id}/end")
async def end_session(session_id: str) -> Dict[str, str]:
    """Force end an interaction session (for interrupts)."""
    interaction_service = get_interaction_service()
    
    summary = await interaction_service.end_session(session_id, reason="forced_end")
    
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "status": "ok",
        "summary": summary
    }
