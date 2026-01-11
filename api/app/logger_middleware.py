import logging
from datetime import datetime
from pathlib import Path
import json

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

class SessionLogger:
    """Logs all decisions, actions, and state changes per game session."""
    
    def __init__(self):
        self.current_session_file = None
        self.session_start_time = None
        
    def start_new_session(self):
        """Start a new logging session (called when Unity connects)."""
        self.session_start_time = datetime.now()
        timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        self.current_session_file = LOGS_DIR / f"session_{timestamp}.log"
        
        with open(self.current_session_file, "w") as f:
            f.write("="*80 + "\n")
            f.write(f"NEW GAME SESSION - {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
    
    def log(self, category: str, message: str, data: dict = None):
        """Log an event with optional structured data."""
        if not self.current_session_file:
            self.start_new_session()
        
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        elapsed = (datetime.now() - self.session_start_time).total_seconds()
        
        with open(self.current_session_file, "a") as f:
            f.write(f"[{timestamp}] +{elapsed:.2f}s | {category}\n")
            f.write(f"  {message}\n")
            if data:
                formatted_data = json.dumps(data, indent=2, default=str)
                for line in formatted_data.split('\n'):
                    f.write(f"    {line}\n")
            f.write("\n")
    
    def log_decision(self, character_id: str, trigger: str, priority: int):
        """Log a decision request."""
        self.log("DECISION REQUEST", f"Character: {character_id}", {
            "trigger": trigger,
            "priority": priority
        })
    
    def log_action(self, character_id: str, action_type: str, props: dict):
        """Log an action being taken."""
        self.log("ACTION EXECUTED", f"Character: {character_id} | Action: {action_type}", {
            "props": props
        })
    
    def log_state_change(self, character_id: str, changes: dict):
        """Log character state changes."""
        self.log("STATE CHANGE", f"Character: {character_id}", changes)
    
    def log_interaction(self, event: str, session_id: str, participants: list, details: dict = None):
        """Log interaction events."""
        self.log("INTERACTION", f"{event} | Session: {session_id[:8]}...", {
            "participants": participants,
            **(details or {})
        })
    
    def log_llm_call(self, purpose: str, character_id: str, response_summary: str):
        """Log LLM calls and responses."""
        self.log("LLM CALL", f"{purpose} for {character_id}", {
            "response": response_summary
        })
    
    def log_error(self, error_type: str, message: str, details: dict = None):
        """Log errors."""
        self.log("ERROR", f"{error_type}: {message}", details)

# Global logger instance
_session_logger = SessionLogger()

def get_session_logger() -> SessionLogger:
    return _session_logger
