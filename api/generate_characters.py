"""
Character and relationship generation script using Claude Opus 4.5.
Run this to populate the database with initial characters.
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

# Import config for thinking setting (shared with llm_service)
from app.config import get_settings


def get_enable_thinking() -> bool:
    """Get thinking setting from config."""
    return get_settings().enable_thinking


def create_message(client, prompt: str, max_tokens_with_thinking: int, max_tokens_without: int, thinking_budget: int):
    """Create a message with or without thinking based on config setting. Uses streaming for long requests."""
    enable_thinking = get_enable_thinking()
    kwargs = {
        "model": "claude-opus-4-5",
        "max_tokens": max_tokens_with_thinking if enable_thinking else max_tokens_without,
        "messages": [{"role": "user", "content": prompt}]
    }
    if enable_thinking:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    
    # Use streaming to avoid timeout on long requests
    collected_text = ""
    collected_thinking = ""
    
    with client.messages.stream(**kwargs) as stream:
        for event in stream:
            if hasattr(event, 'type'):
                if event.type == 'content_block_delta':
                    if hasattr(event.delta, 'text'):
                        collected_text += event.delta.text
                    elif hasattr(event.delta, 'thinking'):
                        collected_thinking += event.delta.thinking
    
    # Return a simple object that mimics the response structure
    class StreamedResponse:
        def __init__(self, text, thinking, enable_thinking):
            from types import SimpleNamespace
            if enable_thinking and thinking:
                self.content = [
                    SimpleNamespace(type="thinking", thinking=thinking),
                    SimpleNamespace(type="text", text=text)
                ]
            else:
                self.content = [SimpleNamespace(type="text", text=text)]
    
    return StreamedResponse(collected_text, collected_thinking, enable_thinking)


def extract_text(response) -> str:
    """Extract text from response, handling both thinking and non-thinking modes."""
    if get_enable_thinking():
        return next(block.text for block in response.content if block.type == "text")
    return response.content[0].text


async def generate_village(
    num_characters: int = 10, 
    house_spaces: Optional[List[str]] = None,
    all_spaces: Optional[List[str]] = None
):
    """Generate characters and relationships for the village.
    
    Args:
        num_characters: Number of characters to generate
        house_spaces: List of house/residential space names. Characters will be assigned homes from this list.
        all_spaces: List of ALL space names in the village (hospital, school, market, etc.) for context.
                   This helps the LLM generate appropriate characters for the village's facilities.
    """
    
    # Initialize clients
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/village_sim")
    mongo_client = AsyncIOMotorClient(mongo_uri)
    db = mongo_client.village_sim  # Explicitly use village_sim database
    
    # Clear existing data
    await db.characters.delete_many({})
    await db.relationships.delete_many({})
    print("Cleared existing characters and relationships.")
    print(f"Extended thinking: {'enabled' if get_enable_thinking() else 'disabled'}")
    
    print(f"Generating {num_characters} characters...")
    if all_spaces:
        print(f"Village spaces: {', '.join(all_spaces)}")
    if house_spaces:
        print(f"Available houses: {', '.join(house_spaces)}")
    
    # Build village context from all spaces
    village_context = ""
    if all_spaces:
        village_context = f"""
## VILLAGE LAYOUT
This village has the following locations: {', '.join(all_spaces)}

Generate characters whose occupations and backgrounds make sense for this village. 
For example, if there's a hospital, consider having a doctor or nurse. If there's a school, consider a teacher. These are not forced obligations, they are examples of what might occur.

HOWEVER: Do not limit yourself to the boring constraints of the village. The point of this simulation is for it to be fun - generate interesting characters that happen to be connected to the village.
"""
    
    # Build house assignment instruction if spaces provided
    house_instruction = ""
    if house_spaces:
        house_instruction = f"""- home_space (assign each character to one of these houses ONLY: {', '.join(house_spaces)})
  IMPORTANT: Distribute characters across the available houses. Some houses can have multiple residents (couples, families, roommates), 
  but not all characters should live in the same house. Consider relationships when assigning homes.
"""
    
    # Shot 1: Generate characters
    character_prompt = f"""Generate {num_characters} unique villagers for a small village simulation.
{village_context}
For each character provide:

- name (first name or first + last)
- age (18-80)
- gender
- race
- occupation (farmer, blacksmith, merchant, baker, teacher, healer, guard, innkeeper, carpenter, weaver, etc.)
- appearance (indices for: top 0-5, bottom 0-5, shoes 0-3, hair 0-7)
- personality_traits (3-5 traits like: kind, grumpy, ambitious, lazy, curious, shy, confident, etc.)
- core_motivations (2-3 life goals)
- ambition_level (0-100)
- confrontational_tendency (0-100)
- background (2-3 sentences of life history)
- initial_desire (what they want to do at the beginning of the simulation - should fit their occupation and personality, e.g. "bake fresh bread", "check on the crops", "go to school", "kiss wife", etc.)
{house_instruction}
Make characters diverse with interesting potential for drama and relationships. Use simple, direct language without fluff, and focus on making it realistic.
Output as a JSON array of objects."""
    
    response = create_message(client, character_prompt, 100000, 40960, 10000)
    
    # Parse characters
    raw_text = extract_text(response)
    
    # Extract JSON from response
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.find("```", start)
        raw_text = raw_text[start:end].strip()
    elif "```" in raw_text:
        start = raw_text.find("```") + 3
        end = raw_text.find("```", start)
        raw_text = raw_text[start:end].strip()
    
    characters = json.loads(raw_text)
    
    # Insert characters into database
    for char in characters:
        char_id = char["name"].lower().replace(" ", "_")
        char["_id"] = char_id
        
        # Use LLM-generated initial desire
        char["current_desire"] = char.pop("initial_desire", "explore the village")
        
        # Extract home_space if provided by LLM
        home_space = char.pop("home_space", None)
        char["home_space"] = home_space
        
        char["current_activity"] = {
            "type": "idle",
            "target": None,
            "description": "idle",
            "started_at": datetime.utcnow()
        }
        char["needs"] = {
            "happiness": 70,
            "energy": 100,
            "hunger": 30,
            "hygiene": 80,
            "health": 100
        }
        char["feelings"] = {
            "anger": 0,
            "sadness": 0,
            "excitement": 20,
            "fear": 0,
            "love": 0
        }
        char["action_log"] = []
        char["memory_log"] = []
        char["is_in_interaction"] = False
        char["active_session_id"] = None
        char["last_known_position"] = None
        char["last_known_space"] = None
        
        await db.characters.insert_one(char)
        home_info = f" (home: {home_space})" if home_space else ""
        print(f"  Created character: {char['name']}{home_info}")
    
    print(f"\nGenerated {len(characters)} characters successfully!")
    
    # Shot 2: Generate relationships
    print(f"\nGenerating relationships...")
    
    names = [c["name"] for c in characters]
    relationship_prompt = f"""Given these villagers: {', '.join(names)}

Generate the relationship network. Not everyone knows everyone - create a realistic small village social graph.
For each relationship provide:
- characters: [name1, name2] (alphabetically sorted, use exact names from the list)
- name1_to_name2: {{"status": "friendly|romantic|antagonistic|neutral", "affection": 0-100, "trust": 0-100, "respect": 0-100}}
- name2_to_name1: {{"status": "friendly|romantic|antagonistic|neutral", "affection": 0-100, "trust": 0-100, "respect": 0-100}}
- background (1-2 sentences explaining their relationship history)

Create interesting dynamics:
- Some childhood friends
- A romantic couple or two
- Some family connections
- A rivalry or conflict
- Some strangers who don't know each other well

Don't create relationships for every possible pair - only for {num_characters * 2} to {num_characters * 3} meaningful relationships. Use simple, direct language without fluff, and focus on making it realistic and grounded in reality (but still interesting). 
Output as a JSON array."""
    
    response = create_message(client, relationship_prompt, 100000, 40960, 10000)
    
    # Parse relationships
    raw_text = extract_text(response)
    
    if "```json" in raw_text:
        start = raw_text.find("```json") + 7
        end = raw_text.find("```", start)
        raw_text = raw_text[start:end].strip()
    elif "```" in raw_text:
        start = raw_text.find("```") + 3
        end = raw_text.find("```", start)
        raw_text = raw_text[start:end].strip()
    
    relationships = json.loads(raw_text)
    
    # Insert relationships into database
    for rel in relationships:
        # Convert names to character IDs
        char_names = rel["characters"]
        char_ids = [name.lower().replace(" ", "_") for name in char_names]
        char_ids_sorted = sorted(char_ids)
        
        rel_id = "_".join(char_ids_sorted)
        
        # Build directional fields
        rel_doc = {
            "_id": rel_id,
            "characters": char_ids_sorted,
            "background": rel["background"],
            "interaction_history": [],
            "is_interacting": False,
            "active_session_id": None
        }
        
        # Add directional feelings
        for i, char_id in enumerate(char_ids):
            other_id = char_ids[1-i]
            direction_key = f"{char_id}_to_{other_id}"
            
            # Get the direction data from the response
            source_key = f"{char_names[i]}_to_{char_names[1-i]}"
            if source_key in rel:
                rel_doc[direction_key] = rel[source_key]
            else:
                # Fallback if not found
                rel_doc[direction_key] = {
                    "status": "neutral",
                    "affection": 50,
                    "trust": 50,
                    "respect": 50
                }
        
        await db.relationships.insert_one(rel_doc)
        print(f"  Created relationship: {' & '.join(char_names)}")
    
    print(f"\nGenerated {len(relationships)} relationships successfully!")
    print(f"\nDatabase populated! Ready to run the simulation.")
    
    mongo_client.close()
    
    return {
        "characters_created": len(characters),
        "relationships_created": len(relationships),
        "character_names": [c["name"] for c in characters]
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate village characters')
    parser.add_argument('--num', type=int, default=10, help='Number of characters to generate')
    parser.add_argument('--houses', nargs='*', help='List of house space names for home assignment')
    parser.add_argument('--spaces', nargs='*', help='List of all space names in the village (for context)')
    args = parser.parse_args()
    
    asyncio.run(generate_village(
        num_characters=args.num, 
        house_spaces=args.houses,
        all_spaces=args.spaces
    ))
