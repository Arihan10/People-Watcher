"""
Load generated characters from JSON into MongoDB.
Clears existing data and creates characters with relationships.
"""

import asyncio
import json
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_DB_URI = os.getenv("MONGO_DB_URI", "mongodb://localhost:27017/ai_life_sim")
DATABASE_NAME = "ai_life_sim"
INPUT_FILE = "generated_characters.json"


async def load_characters_to_mongo():
    """Load characters from JSON file into MongoDB."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_DB_URI)
    db = client[DATABASE_NAME]
    
    print(f"Connected to MongoDB: {MONGO_DB_URI}")
    
    # Load JSON file
    print(f"\nLoading characters from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    characters = data['characters']
    metadata = data.get('metadata', {})
    
    print(f"Found {len(characters)} characters")
    print(f"Generated at: {metadata.get('generated_at', 'unknown')}")
    print(f"Setting: {metadata.get('setting', 'unknown')}")
    
    # Clear existing data
    print("\n=== Clearing existing data ===")
    chars_deleted = await db.characters.delete_many({})
    rels_deleted = await db.relationships.delete_many({})
    sessions_deleted = await db.interaction_sessions.delete_many({})
    
    print(f"Deleted: {chars_deleted.deleted_count} characters, "
          f"{rels_deleted.deleted_count} relationships, "
          f"{sessions_deleted.deleted_count} sessions")
    
    # Insert characters
    print("\n=== Inserting characters ===")
    
    # Prepare character documents
    char_docs = []
    name_to_id = {}  # Map names to IDs for relationship creation
    
    for char in characters:
        doc = {
            "name": char["name"],
            "age": char["age"],
            "appearance": char["appearance"],
            "race": char["race"],
            "gender": char["gender"],
            "occupation": char["occupation"],
            "background": char["background"],
            "personality_traits": char.get("personality_traits", []),
            "needs": char.get("needs", {
                "happiness": 50,
                "energy": 50,
                "hunger": 50,
                "hygiene": 50
            }),
            "current_desire": None,
            "action_log": [],
            "memory_log": [],
            "relationships": []  # Will populate with IDs after relationship creation
        }
        char_docs.append(doc)
    
    # Insert all characters
    result = await db.characters.insert_many(char_docs)
    inserted_ids = result.inserted_ids
    
    # Create name to ID mapping
    for i, char in enumerate(characters):
        name_to_id[char["name"]] = str(inserted_ids[i])
    
    print(f"Inserted {len(inserted_ids)} characters")
    
    # Create relationships (bidirectional)
    print("\n=== Creating relationships ===")
    
    relationships_to_insert = []
    character_relationship_map = {}  # Track which characters each character knows
    processed_pairs = set()  # Track which pairs we've processed
    
    for i, char in enumerate(characters):
        char_id = str(inserted_ids[i])
        char_name = char["name"]
        
        if char_id not in character_relationship_map:
            character_relationship_map[char_id] = []
        
        for rel in char.get("relationships", []):
            target_name = rel["target_name"]
            
            # Find target character ID
            if target_name not in name_to_id:
                print(f"Warning: Relationship target '{target_name}' not found for {char_name}")
                continue
            
            target_id = name_to_id[target_name]
            
            # Create pair key (sorted to avoid duplicates)
            pair_key = tuple(sorted([char_id, target_id]))
            
            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)
                
                # Find the reverse relationship if it exists
                target_char = next((c for c in characters if c["name"] == target_name), None)
                reverse_rel = None
                if target_char:
                    reverse_rel = next((r for r in target_char.get("relationships", []) if r.get("target_name") == char_name), None)
                
                # Create bidirectional relationship
                relationship_doc = {
                    "character_id_1": char_id,
                    "character_id_2": target_id,
                    
                    # Char1's perspective (current character)
                    "char1_relationship_type": rel.get("relationship_type", "Acquaintance"),
                    "char1_summary": rel.get("relationship_summary", ""),
                    "char1_score": rel.get("relationship_score", 50),
                    "char1_interaction_history": [],
                    
                    # Char2's perspective (target character)
                    "char2_relationship_type": reverse_rel.get("relationship_type", "Acquaintance") if reverse_rel else "Acquaintance",
                    "char2_summary": reverse_rel.get("relationship_summary", "") if reverse_rel else "",
                    "char2_score": reverse_rel.get("relationship_score", 50) if reverse_rel else 50,
                    "char2_interaction_history": [],
                    
                    "current_interaction_state": "none"
                }
                relationships_to_insert.append(relationship_doc)
                
                # Track relationships for both characters
                if target_id not in character_relationship_map.get(char_id, []):
                    character_relationship_map.setdefault(char_id, []).append(target_id)
                if char_id not in character_relationship_map.get(target_id, []):
                    character_relationship_map.setdefault(target_id, []).append(char_id)
    
    if relationships_to_insert:
        rel_result = await db.relationships.insert_many(relationships_to_insert)
        print(f"Inserted {len(rel_result.inserted_ids)} relationships")
    else:
        print("No relationships to insert")
    
    # Update character relationship lists
    print("\n=== Updating character relationship lists ===")
    for char_id, related_ids in character_relationship_map.items():
        await db.characters.update_one(
            {"_id": inserted_ids[int([i for i, id in enumerate(inserted_ids) if str(id) == char_id][0])]},
            {"$set": {"relationships": related_ids}}
        )
    
    print(f"Updated relationship lists for {len(character_relationship_map)} characters")
    
    # Close connection
    client.close()
    
    print("\n=== Load Complete ===")
    print(f"Database: {DATABASE_NAME}")
    print(f"Characters: {len(inserted_ids)}")
    print(f"Relationships: {len(relationships_to_insert)}")
    print(f"\nYou can now start the API server with: uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(load_characters_to_mongo())

