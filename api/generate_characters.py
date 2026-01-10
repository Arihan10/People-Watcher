"""
Character Generation Script
Uses Claude 4.5 Sonnet to generate a small rural town with 20 characters.
Map includes: Park, Pool, Soccer Field, Farmer Market, Campfire, School, Farm, Library, Hospital, and Houses.
Two-shot approach:
1. Generate background stories for all characters
2. Parse and populate relationships, demographics, appearances, and locations
"""

import os
import json
import asyncio
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configuration
NUM_CHARACTERS = 20
SETTING = "small rural town with park, pool, soccer field, farmer market, school, farm, library, and hospital"
OUTPUT_FILE = "generated_characters.json"

# Asset mappings for reference
HAIR_STYLES = {
    0: "afro 1", 1: "afro 2", 2: "afro 3", 3: "buzzcut",
    4: "curly 1", 5: "curly 2", 6: "medium 1", 7: "medium 2",
    8: "short 1", 9: "short 2", 10: "short 3", 11: "short 4",
    12: "bun", 13: "ponytail", 14: "double buns", 15: "twintails"
}

SHOES = {
    0: "girly boots", 1: "orange running shoes", 2: "sandals",
    3: "slippers", 4: "boots", 5: "sketchers", 6: "worker boots"
}

BOTTOMS = {
    0: "black pants", 1: "shorts", 2: "skirt",
    3: "jeans", 4: "long shorts (girly)", 5: "baggy joggers"
}

TOPS = {
    0: "white gym shirt", 1: "jacket", 2: "sweater", 3: "button shirt orange",
    4: "reese esque sweater with shirt underneath", 5: "flanel over white t",
    6: "crop top with yellow jacket", 7: "wheres wally striped shirt",
    8: "green hoodie", 9: "shirt with tie", 10: "suit top"
}

JOBS_AND_LOCATIONS = {
    "School": ["Teacher", "Student", "Principal"],
    "Hospital": ["Nurse", "Doctor"],
    "Farm": ["Farmer", "Farmhand"],
    "Library": ["Librarian", "Library Assistant"],
    "Farmer Market": ["Market Vendor", "Produce Seller"],
    "Pool": ["Lifeguard", "Pool Attendant"],
    "Soccer Field": ["Soccer Coach", "Athlete"],
    "Park": ["Park Ranger", "Groundskeeper"],
    "Houses": ["Retired", "Homemaker", "Remote Worker", "Chef", "Artist"],
    "General": ["Town Mayor", "Handyman", "Delivery Driver"]
}

ALL_JOBS = [job for jobs in JOBS_AND_LOCATIONS.values() for job in jobs]

MAP_LOCATIONS = [
    "Park", "Pool", "Soccer Field", "Farmer Market", "Campfire Area",
    "School", "Farm", "Library", "Hospital", "House 1", "House 2",
    "House 3", "House 4", "House 5"
]


async def generate_character_backgrounds(client: AsyncAnthropic) -> str:
    """
    Shot 1: Generate background stories for all 20 characters.
    Returns a narrative with all character backgrounds.
    """
    
    print("Shot 1: Generating character backgrounds...")
    
    locations_desc = "\n".join([f"- {loc}: {', '.join(jobs)}" for loc, jobs in JOBS_AND_LOCATIONS.items()])
    
    prompt = f"""You are a creative writer designing characters for a {SETTING} with {NUM_CHARACTERS} people.

Create {NUM_CHARACTERS} unique characters with rich, interconnected backgrounds. This is a close-knit rural community.

THE TOWN MAP INCLUDES:
- Park (peaceful area for gatherings)
- Pool (community swimming pool)
- Soccer Field (sports and recreation)
- Farmer Market stands (local produce and goods)
- Campfire area (community gathering spot)
- School (middle building - education center)
- Farm (back building with cows and chickens)
- Library (left building - knowledge center)
- Hospital/Nurse station (rightmost building with beds and IV stands)
- Several residential houses

JOB DISTRIBUTION BY LOCATION:
{locations_desc}

Requirements:
- Include families (parents, children, siblings, spouses) - but families should have INTERNAL CONFLICTS
- Mix of ages (children 5-17, adults 18-60, elders 60+)
- Various occupations from the list above
- Complex relationships (friends, rivals, family, romantic interests)
- Diverse ethnicities (realistic human races - White, Black, Asian, Hispanic, Middle Eastern, etc.)
- Each person should have meaningful connections to at least 2-3 others
- IMPORTANT: CREATE DRAMA AND TENSION:
  * Include love triangles, unrequited love, secret crushes
  * Create rivalries, grudges, old conflicts that still simmer
  * Add family drama (estranged siblings, disappointed parents, rebellious children)
  * Include workplace tensions, professional jealousies
  * Create conflicting goals and competing interests between characters
  * Add secrets, betrayals, and unresolved issues
- IMPORTANT: Each character needs clear BEHAVIORAL TRAITS that guide their decisions:
  * Ambition level (low/medium/high)
  * Confrontational tendency (low/medium/high)
  * Sociability (low/medium/high)
  * Core life motivation (what they want: family, love, power, knowledge, safety, adventure, etc.)
  * Other decision-guiding traits (protective, curious, cautious, impulsive, etc.)

For EACH of the {NUM_CHARACTERS} characters, write a background paragraph that includes:
1. Their name, age, and occupation (from the jobs list above)
2. Where they work/spend time (specific location on the map)
3. Their core personality dimensions (ambition level, confrontational tendency)
4. What they want in life (core motivations like "take care of family", "find love", "gain respect", "escape poverty")
5. Their family connections AND family tensions/conflicts
6. Important relationships with other townspeople - emphasize DRAMA:
   - Romantic interests (unrequited love, love triangles, complicated attractions)
   - Rivalries and antagonistic relationships
   - Betrayals, grudges, or past conflicts
   - Professional jealousies or competing ambitions
7. A brief life story with emphasis on conflicts and tensions

Format each character as:
---
CHARACTER [number]
[Background paragraph]
---

Make the town feel like a DRAMATIC SOAP OPERA with interconnected stories, LOTS of conflicts, romantic tensions, family drama, rivalries, and complicated dynamics. This should feel like a reality TV show where everyone has beef with someone!"""

    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    backgrounds = response.content[0].text
    print(f"Generated {len(backgrounds)} characters of background text")
    return backgrounds


async def parse_characters_to_structured_data(client: AsyncAnthropic, backgrounds: str) -> list:
    """
    Shot 2: Parse backgrounds into structured character data with relationships.
    Returns list of character dictionaries.
    """
    
    print("\nShot 2: Parsing into structured data...")
    
    # Create appearance codes reference for the LLM
    appearance_guide = f"""
APPEARANCE ASSET CODES (choose appropriate codes):

Hair (0-15): {', '.join(f"{k}={v}" for k, v in HAIR_STYLES.items())}
Shoes (0-6): {', '.join(f"{k}={v}" for k, v in SHOES.items())}
Bottom (0-5): {', '.join(f"{k}={v}" for k, v in BOTTOMS.items())}
Top (0-10): {', '.join(f"{k}={v}" for k, v in TOPS.items())}
"""
    
    jobs_list = ', '.join(ALL_JOBS)
    
    prompt = f"""Parse the following character backgrounds into structured JSON data.

{backgrounds}

{appearance_guide}

For EACH character, create a JSON object with:
{{
  "name": "Full Name",
  "age": <number>,
  "race": "White/Black/Asian/Hispanic/Middle Eastern/Native American/Mixed/etc (realistic human ethnicities)",
  "gender": "Male/Female/Non-binary",
  "occupation": "occupation from: {jobs_list}",
  "background": "Their full background story (2-3 sentences)",
  "personality_traits": [
    "ambition: low/medium/high",
    "confrontational: low/medium/high",
    "sociable: low/medium/high",
    "core_motivation: [specific goal like 'take care of family', 'find love', 'gain respect', 'become wealthy', 'seek adventure', 'protect others', etc.]",
    "[other relevant behavioral traits that will guide their decisions]",
    ...
  ],
  "appearance": {{
    "hair": <0-15>,
    "shoes": <0-6>,
    "bottom": <0-5>,
    "top": <0-10>
  }},
  "relationships": [
    {{
      "target_name": "Name of other character",
      "relationship_type": "Family/Friend/Romantic/Professional/Rival",
      "relationship_summary": "How this character feels about the target",
      "relationship_score": <-100 to 100>
    }}
  ],
  "needs": {{
    "happiness": <0-100>,
    "energy": <0-100>,
    "hunger": <0-100>,
    "hygiene": <0-100>,
    "anger": <0-100>,
    "sadness": <0-100>
  }}
}}

IMPORTANT:
1. Choose appearance codes that fit rural/modern setting (e.g., worker boots for farmers, casual wear for students)
2. PERSONALITY TRAITS must be DECISION-GUIDING, not just descriptive. Include:
   - "ambition: low/medium/high" (how driven are they?)
   - "confrontational: low/medium/high" (do they avoid or seek conflict?)
   - "sociable: low/medium/high" (do they seek company or solitude?)
   - "core_motivation: [specific goal]" (what do they want in life?)
   - Additional behavioral traits that affect decisions (protective, curious, cautious, impulsive, loyal, etc.)
3. Create relationships BETWEEN the characters (use their names) - EMPHASIZE DRAMA:
   - Each character should have 4-6 relationships minimum
   - AT LEAST 30-40% of relationships should be negative/tense (scores below 20)
   - Include love triangles (Person A loves Person B who loves Person C)
   - Include rivalries and antagonistic relationships (negative scores)
   - Include complicated family dynamics (even family can have low scores due to conflict)
   - Use relationship_type "Romantic" for crushes, attractions, or complicated feelings
   - Use relationship_type "Rival" for antagonistic relationships
4. Ensure family relationships are bidirectional (if A is B's parent, B is A's child) - but scores can differ!
5. Relationship scores: 
   - 80-100 (deep love/very positive) 
   - 40-80 (positive/friendly)
   - 20-40 (neutral/awkward)
   - 0-20 (tense/uncomfortable)
   - -20-0 (dislike/conflict)
   - -40--20 (strong dislike/rivalry)
   - -100--40 (hatred/hostility)
   USE THE FULL RANGE! Don't just make everyone friendly.
6. Set reasonable initial needs (most people around 50-70)

Return ONLY a valid JSON array of {NUM_CHARACTERS} character objects. No markdown, no explanation."""

    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16000,
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )
    
    json_text = response.content[0].text.strip()
    
    # Remove markdown code blocks if present
    if json_text.startswith("```"):
        json_text = json_text.split("```")[1]
        if json_text.startswith("json"):
            json_text = json_text[4:]
        json_text = json_text.strip()
    
    try:
        characters = json.loads(json_text)
        print(f"Successfully parsed {len(characters)} characters")
        return characters
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response text:\n{json_text[:500]}...")
        raise


async def main():
    """Main generation workflow."""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment")
    
    client = AsyncAnthropic(api_key=api_key)
    
    print(f"=== Rural Town Character Generator ===")
    print(f"Generating {NUM_CHARACTERS} characters for {SETTING}")
    print(f"Map Locations: {', '.join(MAP_LOCATIONS[:5])}...")
    print(f"Using Claude 4.5 Sonnet\n")
    
    # Shot 1: Generate backgrounds
    backgrounds = await generate_character_backgrounds(client)
    
    # Shot 2: Parse to structured data
    characters = await parse_characters_to_structured_data(client, backgrounds)
    
    # Add metadata
    output_data = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "setting": SETTING,
            "num_characters": len(characters),
            "model": "claude-sonnet-4-5-20250929"
        },
        "characters": characters
    }
    
    # Save to JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== Generation Complete ===")
    print(f"Characters saved to: {OUTPUT_FILE}")
    print(f"\nCharacters generated:")
    for i, char in enumerate(characters, 1):
        print(f"{i}. {char['name']} - {char['age']}yo {char['occupation']}")
        print(f"   Relationships: {len(char.get('relationships', []))}")
    
    # Statistics
    total_relationships = sum(len(c.get('relationships', [])) for c in characters)
    print(f"\nTotal relationships: {total_relationships}")
    print(f"Average relationships per character: {total_relationships / len(characters):.1f}")
    
    print(f"\nNext step: Run 'python load_to_mongo.py' to load into database")


if __name__ == "__main__":
    asyncio.run(main())

