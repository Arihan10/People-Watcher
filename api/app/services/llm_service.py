import anthropic
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..config import get_settings
from ..models import Action, ActionType
from ..logger_middleware import get_session_logger

logger = logging.getLogger(__name__)
session_logger = get_session_logger()

VALID_ACTION_TYPES = {e.value for e in ActionType}


class LLMService:
    """Service for LLM interactions using Claude Opus 4.5."""
    
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-opus-4-5"
        self.enable_thinking = settings.enable_thinking
    
    def _extract_text(self, response) -> str:
        """Extract text from response, handling both thinking and non-thinking modes."""
        if self.enable_thinking:
            return next(block.text for block in response.content if block.type == "text")
        return response.content[0].text
    
    async def decide(
        self,
        character: Dict[str, Any],
        trigger: str,
        space_states: List[Dict],
        global_context: Dict,
        nearby_relationships: List[Dict],
        is_in_interaction: bool = False,
        interaction_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Core decision-making. Returns state changes and action.
        """
        prompt = self._build_decide_prompt(
            character, trigger, space_states, 
            global_context, nearby_relationships,
            is_in_interaction, interaction_context
        )
        
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": 16000 if self.enable_thinking else 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            if self.enable_thinking:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
            
            response = await self.client.messages.create(**kwargs)
            
            raw_text = self._extract_text(response)
            parsed = self._parse_decision(raw_text)
            
            # Log LLM response
            session_logger.log_llm_call(
                "decide",
                character.get("_id", "unknown"),
                f"Action: {parsed['action']['actionType']}, Thought: {parsed.get('inner_thought', 'N/A')[:100]}"
            )
            
            return parsed
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {
                "inner_thought": "Error occurred",
                "state_changes": {},
                "action": {"actionType": "none", "props": {}}
            }
    
    def _build_decide_prompt(
        self,
        character: Dict,
        trigger: str,
        space_states: List[Dict],
        global_context: Dict,
        nearby_relationships: List[Dict],
        is_in_interaction: bool,
        interaction_context: Optional[Dict]
    ) -> str:
        """Build the decision prompt from context."""
        
        # Format feelings
        feelings = character.get("feelings", {})
        feelings_str = ", ".join([f"{k.title()} {v}%" for k, v in feelings.items()])
        
        # Format activity
        activity = character.get("current_activity", {})
        activity_desc = activity.get("description", "idle")
        activity_started = activity.get("started_at", "")
        
        # Format action log
        action_log = character.get("action_log", [])[-5:]
        action_str = "\n".join([f"  - {a.get('action', '')}" for a in action_log]) or "  - (no recent actions)"
        
        # Format memory log
        memory_log = character.get("memory_log", [])[-5:]
        memory_str = "\n".join([f"  - {m.get('observation', '')}" for m in memory_log]) or "  - (no recent memories)"
        
        # Format relationships
        rel_str = ""
        for rel in nearby_relationships:
            char_id = character["_id"]
            other_chars = [c for c in rel.get("characters", []) if c != char_id]
            if not other_chars:
                continue
            other_name = other_chars[0]
            direction_key = f"{char_id}_to_{other_name}"
            direction = rel.get(direction_key, {})
            
            status = direction.get("status", "neutral")
            affection = direction.get("affection", 50)
            trust = direction.get("trust", 50)
            
            history = rel.get("interaction_history", [])
            last_interaction = history[-1].get("summary", "No recent interactions") if history else "No interactions yet"
            
            rel_str += f"- {other_name.title()}: {status}, Affection {affection}%, Trust {trust}%\n"
            rel_str += f"  Last interaction: \"{last_interaction}\"\n"
        
        if not rel_str:
            rel_str = "- No nearby characters with established relationships"
        
        # Format spaces
        space_str = ""
        for space in space_states:
            space_str += f"Space: {space.get('space_name', '')}\n"
            space_str += f"- People here: {', '.join(space.get('characters_present', [])) or 'none'}\n"
            space_str += f"- Objects: {', '.join(space.get('available_objects', [])) or 'none'}\n"
            space_str += f"- What's happening: {space.get('description', 'quiet')}\n\n"
        
        prompt = f"""You are {character['name']}, a {character['age']}-year-old {character['gender']} {character['race']} who works as a {character['occupation']}.

## YOUR PERSONALITY
Traits: {', '.join(character.get('personality_traits', []))}
Ambition: {character.get('ambition_level', 50)}/100
Confrontational: {character.get('confrontational_tendency', 50)}/100
Core Motivations: {', '.join(character.get('core_motivations', []))}

## YOUR BACKGROUND
{character.get('background', 'No background provided')}

## YOUR CURRENT STATE
What you want: {character.get('current_desire', 'unsure')}
Current activity: {activity_desc}
Needs: Happiness {character['needs']['happiness']}%, Energy {character['needs']['energy']}%, Hunger {character['needs']['hunger']}%, Hygiene {character['needs']['hygiene']}%, Health {character['needs']['health']}%
Feelings: {feelings_str}

NOTE: If your current activity shows you are already doing something (like walking somewhere), you should usually choose action "none" to continue that activity unless something important requires your attention.

## RECENT HISTORY
Last 5 actions:
{action_str}

Recent memories:
{memory_str}

## RELATIONSHIPS WITH PEOPLE NEARBY
{rel_str}

NOTE: You can only initiate_interaction with people who are in the same space as you right now.

## CURRENT ENVIRONMENT
{space_str}

## WORLD STATE
Time: {global_context.get('time', 'daytime')}

## KNOWN LOCATIONS IN THE VILLAGE
You can move to any of these places or any named object/character:
{', '.join(global_context.get('all_spaces', []))}

Other characters' locations:
{chr(10).join([f"- {loc.get('character_name')}: at {loc.get('space_name', 'unknown')}" for loc in global_context.get('character_locations', [])[:10]])}

---

## WHAT JUST HAPPENED
{trigger}

---
"""
        
        # Add interaction context if in conversation
        if is_in_interaction and interaction_context:
            other_participant = [p for p in interaction_context.get("participants", []) if p != character["_id"]][0]
            session_type = interaction_context.get("session_type", "dialog")
            
            prompt += f"""
## CURRENT INTERACTION
You are in a {session_type} with {other_participant}.
Conversation so far:
"""
            turns = interaction_context.get("turns", [])
            for turn in turns[-10:]:  # Last 10 turns
                char = turn.get("character", "")
                action_type = turn.get("action_type", "")
                content = turn.get("content", "")
                prompt += f"  {char}: [{action_type}] {content}\n"
            
            prompt += """
It's your turn. You may:
- speak (say something)
- leave (end the interaction)
- fight_action (punch, kick, block, etc.)
- romance_action (kiss, hug, hold hands, etc.)

"""
        
        prompt += """---

Decide what to do based on your personality and the situation.

IMPORTANT GUIDELINES:
- If your current activity already shows you doing something (e.g., "walking to Library"), choose action "none" to CONTINUE that activity - don't re-issue the same action!
- Only choose a NEW action if you want to CHANGE what you're doing or if you've completed/arrived somewhere.
- When idle, actively pursue your desires - take action to achieve your goals.

Respond with ONLY valid JSON:
{
  "inner_thought": "1-2 sentence thought process",
  "state_changes": {
    "current_desire": "new desire if changed, omit if unchanged",
    "current_activity": "ONLY if starting a NEW action - describe what you're now doing in third person, e.g. 'Maria is walking to the library to find books about history'",
    "feelings": {"anger": 10},
    "needs": {"energy": -5},
    "add_memory": "optional observation to remember"
  },
  "action": {
    "actionType": "move|use_object|speak|initiate_interaction|speak_in_interaction|fight_action|romance_action|leave_interaction|none",
    "props": {}
  }
}

State changes notes:
- current_activity: ONLY include this field when you are starting a NEW action (not "none"). Write in third person describing what you're doing and why, e.g. "Tommy is hurrying to the market to buy supplies before it closes". Do NOT include this field if choosing action "none".

Action props by type:
- move: {"destination": "market"} - destination can be a space name, object name, or character name
- use_object: {"object_name": "sink", "flavor": "scrubbing dishes thoughtfully"}
- speak: {"dialogue": "Hey, stop fighting!"} - write SHORT, candid, conversational dialogue that would be realistic for an active, back-and-forth conversation. Write realistially.
- initiate_interaction: {"target_character": "sarah", "type": "dialog|fight|romance", "opening": "Hey Sarah!"}
- speak_in_interaction: {"dialogue": "How are you doing?"}
- fight_action: {"action": "punch|kick|block|dodge"}
- romance_action: {"action": "kiss|hug|hold_hands"}
- leave_interaction: {}
- none: {} (use this to CONTINUE your current activity)

CRITICAL: DO NOT REFERENCE OBJECTS, PLACES, PEOPE, ETC. THAT ARE NOT STATED TO EXIST. ALSO, INTERACT WITH OTHER CHARACTERS AS MUCH AS POSSIBLE. DON'T JUST DO SHIT ALONE! ALSO: You should actively pursue your desires! If you want to visit the market, USE THE MOVE ACTION. Don't just stand around - take action to achieve your goals.
"""
        
        return prompt
    
    def _parse_decision(self, raw_response: str) -> Dict[str, Any]:
        """Parse LLM response, with error handling."""
        try:
            # Try to extract JSON from response
            if "```json" in raw_response:
                start = raw_response.find("```json") + 7
                end = raw_response.find("```", start)
                raw_response = raw_response[start:end].strip()
            elif "```" in raw_response:
                start = raw_response.find("```") + 3
                end = raw_response.find("```", start)
                raw_response = raw_response[start:end].strip()
            
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {raw_response[:200]}")
            return {
                "inner_thought": "Error parsing response",
                "state_changes": {},
                "action": {"actionType": "none", "props": {}}
            }
        
        if "action" not in data:
            logger.error("Missing 'action' field in LLM response")
            return {
                "inner_thought": data.get("inner_thought", ""),
                "state_changes": {},
                "action": {"actionType": "none", "props": {}}
            }
        
        action_type = data["action"].get("actionType", "none")
        if action_type not in VALID_ACTION_TYPES:
            logger.warning(f"Unknown action type: {action_type}, defaulting to none")
            action_type = "none"
        
        return {
            "inner_thought": data.get("inner_thought", ""),
            "state_changes": data.get("state_changes", {}),
            "action": {
                "actionType": action_type,
                "props": data["action"].get("props", {})
            }
        }
    
    async def summarize_interaction(self, session: Dict[str, Any]) -> str:
        """Generate a summary of an interaction for relationship history."""
        participants = session.get("participants", [])
        session_type = session.get("session_type", "dialog")
        turns = session.get("turns", [])
        
        # Build conversation history
        convo = ""
        for turn in turns:
            char = turn.get("character", "")
            content = turn.get("content", "")
            convo += f"{char}: {content}\n"
        
        prompt = f"""Summarize this {session_type} interaction between {' and '.join(participants)} in 1-2 sentences.
Focus on what happened and the emotional/relationship impact.

Conversation:
{convo}

Provide a brief summary:"""
        
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": 10000 if self.enable_thinking else 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            if self.enable_thinking:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4000}
            
            response = await self.client.messages.create(**kwargs)
            return self._extract_text(response).strip()
        except Exception as e:
            logger.error(f"Error summarizing interaction: {e}")
            return f"{session_type.title()} between {' and '.join(participants)}"
    
    async def generate_space_context(
        self,
        space_name: str,
        characters: List[str],
        objects: List[str],
        previous_activities: List[str]
    ) -> str:
        """Generate/update space description."""
        
        prompt = f"""Generate a brief, atmospheric description of what's happening in {space_name}.

Present: {', '.join(characters) if characters else 'empty'}
Objects: {', '.join(objects) if objects else 'none'}
Previous activities: {', '.join(previous_activities) if previous_activities else 'none'}

Create a 1-2 sentence description capturing the current atmosphere and activities. Be concise and evocative."""
        
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": 100000 if self.enable_thinking else 1024,
                "messages": [{"role": "user", "content": prompt}]
            }
            if self.enable_thinking:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 2000}
            
            response = await self.client.messages.create(**kwargs)
            return self._extract_text(response).strip()
        except Exception as e:
            logger.error(f"Error generating space context: {e}")
            return f"{space_name} is quiet."


# Global instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
