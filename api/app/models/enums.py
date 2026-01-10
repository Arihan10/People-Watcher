from enum import Enum


class InteractionState(str, Enum):
    """Enum for the current state of interaction between characters."""
    
    NONE = "none"
    DIALOG = "dialog"
    FIGHTING = "fighting"
    ROMANCE = "romance"

