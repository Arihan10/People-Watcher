# AI Life Simulation - Unity Backend API

FastAPI backend for an AI-powered life simulation game built with Unity. This API manages character AI, relationships, and conversations using Claude 4.5 Sonnet.

## 🎯 Unity Integration Focus

This backend is designed to work seamlessly with Unity:

-   **Unity owns:** Positions, movement, physics, rendering, spatial data
-   **Backend owns:** Character AI, relationships, memories, dialogue generation

## Features

-   **AI Character Decisions** - Characters decide what to do based on personality and context
-   **Bidirectional Relationships** - Asymmetric feelings (A likes B more than B likes A)
-   **AI-Generated Dialogue** - Realistic conversations based on personality and relationships
-   **Automatic Relationship Creation** - First interactions create relationships automatically
-   **Memory Formation** - Characters remember conversations and events
-   **Space Context Generation** - AI describes what's happening in locations

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Create `.env` file:

```env
MONGO_DB_URI=mongodb://localhost:27017/ai_life_sim
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Generate & Load Characters

```bash
# Generate 20 medieval town characters with AI
python generate_characters.py

# Load into MongoDB
python load_to_mongo.py
```

### 4. Start API Server

```bash
uvicorn app.main:app --reload
```

API runs at: `http://localhost:8000`
Docs at: `http://localhost:8000/docs`

---

## 📡 API Endpoints for Unity

### Characters

#### Get All Characters

```
GET /characters
```

Returns all characters with full data (profile, needs, desires, relationships list)

**Unity Use:** Call on game start to populate world

#### Get Character by ID

```
GET /characters/{character_id}
```

Returns specific character with updated state

**Unity Use:** Refresh character after interactions

#### Use Object

```
POST /characters/{character_id}/use/{object_name}
```

Character interacts with object, returns AI-generated emoji flavor text

**Request:** No body needed
**Response:**

```json
{
	"character_name": "Marcus Blackwood",
	"object_name": "fountain",
	"flavor_text": "splashing water playfully 💦😄",
	"timestamp": "..."
}
```

**Unity Use:** Display as subtitle above character

#### Save All Character Positions

```
POST /characters/save-positions
```

Save positions for all characters (Unity calls this on shutdown)

**Request:**

```json
{
	"positions": [
		{
			"character_id": "marcus_id",
			"position": { "x": 10.5, "y": 3.2 }
		},
		{
			"character_id": "isabella_id",
			"position": { "x": -5.3, "y": 8.1 }
		}
	]
}
```

**Response:**

```json
{
	"updated_count": 2,
	"failed_count": 0,
	"message": "Updated 2/2 character positions successfully"
}
```

**Unity Use:** Call on game shutdown to persist all character positions

#### Make Decision (.decide)

```
POST /characters/{character_id}/decide
```

AI decides what character should do next based on full context

**Request:**

```json
{
	"trigger_source": "character moved to new location",
	"space_context": {
		"current_space": "Town Square",
		"description": "Marcus is sitting. Isabella is reading.",
		"nearby_characters": ["Isabella Cortez", "Sophie Blackwood"],
		"available_objects": ["fountain", "bench", "notice_board"]
	},
	"global_context": {
		"time": "afternoon",
		"day": 1,
		"weather": "sunny"
	}
}
```

**Response:**

```json
{
	"character_name": "Marcus Blackwood",
	"trigger_source": "character moved to new location",
	"state_changes": [
		{ "current_desire": "talk to Isabella" },
		{ "happiness": 65 }
	],
	"action": {
		"actionType": "initiate_conversation",
		"props": {
			"target_character": "Isabella Cortez",
			"interaction_type": "dialog"
		}
	},
	"reasoning": "Saw Isabella nearby and wants to spend time with her",
	"timestamp": "..."
}
```

**Action Types:**

-   `move` - props: `{destination: "space_name", destination_type: "place/object/person"}`
-   `initiate_conversation` - props: `{target_character: "name", interaction_type: "dialog/fight/romance"}`
-   `use_object` - props: `{object_name: "fountain"}`
-   `wait` - props: `{}`
-   `continue` - props: `{}`

**Unity Use:** Execute the returned action

---

### Relationships

#### Get Character Relationships

```
GET /relationships/character/{character_id}
```

Returns all relationships for a character with perspectives extracted

**Response:**

```json
[
  {
    "_id": "...",
    "character_id_1": "marcus_id",
    "character_id_2": "isabella_id",
    "my_perspective": {
      "other_character_id": "isabella_id",
      "relationship_type": "Romantic",
      "summary": "Has a crush on her",
      "score": 80,
      "interaction_history": [...]
    },
    "their_perspective": {
      "relationship_type": "Friendly",
      "summary": "Finds him annoying but amusing",
      "score": 45
    },
    "current_interaction_state": "none"
  }
]
```

**Note:** Relationships are bidirectional - single document shows both perspectives

---

### Context Generation

#### Generate Space Context

```
POST /context/generate-space-context
```

Unity sends space name + character names, backend generates description

**Request:**

```json
{
	"space_name": "Town Square",
	"characters_present": [
		"Marcus Blackwood",
		"Isabella Cortez",
		"Sophie Blackwood"
	]
}
```

**Response:**

```json
{
	"space_name": "Town Square",
	"description": "Marcus is sitting on the fountain edge. Isabella is organizing her stall. Sophie is running around exploring."
}
```

**Unity Use:** Generate scene descriptions when characters enter/leave spaces

---

### Interaction Sessions

#### Start Conversation

```
POST /interaction-sessions/
```

Start AI conversation between characters

**Request:**

```json
{
	"character_ids": ["marcus_id", "isabella_id"],
	"interaction_type": "dialog"
}
```

**Response:** Session with session_id

**Auto-Creates:** Relationships if first meeting

**Unity Use:** When characters should talk (proximity, player trigger, etc.)

#### Get Session

```
GET /interaction-sessions/{session_id}
```

Get current conversation state

**Unity Use:** Check conversation status

#### Advance Conversation

```
POST /interaction-sessions/{session_id}/advance
```

AI generates next message in conversation

**Response:**

```json
{
	"messages": [
		{
			"character_name": "Marcus Blackwood",
			"content": "Hey Isabella! Want to explore the forest?",
			"timestamp": "..."
		}
	],
	"current_turn": "isabella_id",
	"is_active": true
}
```

**Unity Use:** Display dialogue in UI

#### End Conversation

```
POST /interaction-sessions/{session_id}/end
```

End conversation, AI generates summary and updates relationships

**Auto-Updates:**

-   Both characters' relationship scores (can be different!)
-   Interaction histories
-   Character memories
-   Unlocks characters

**Unity Use:** When conversation should end

---

## 🎮 Unity Integration Flow

### Game Initialization

```csharp
async void Start() {
    // Load all characters
    var characters = await GET("/characters");

    // Instantiate character GameObjects at saved positions
    foreach (var character in characters) {
        InstantiateCharacter(character, character.position);
    }
}
```

### Game Shutdown (Save Positions)

```csharp
async void OnApplicationQuit() {
    // Gather all character positions
    var positions = new List<CharacterPosition>();

    foreach (var character in allCharacters) {
        positions.Add(new CharacterPosition {
            character_id = character.id,
            position = new Position {
                x = character.transform.position.x,
                y = character.transform.position.y
            }
        });
    }

    // Save all positions in one call
    await POST("/characters/save-positions", new {
        positions = positions
    });

    Debug.Log("All character positions saved!");
}
```

### Character Movement

```csharp
async void OnCharacterReachDestination(Character character, string spaceName) {
    // 1. Generate space context
    var nearbyCharNames = GetCharacterNamesInSpace(spaceName);
    var spaceContext = await POST("/context/generate-space-context", new {
        space_name = spaceName,
        characters_present = nearbyCharNames
    });

    // 2. Display description
    ShowSpaceDescription(spaceContext.description);

    // 3. Character makes decision about new location
    var decision = await POST($"/characters/{character.id}/decide", new {
        trigger_source = "arrived at new location",
        space_context = new {
            current_space = spaceName,
            description = spaceContext.description,
            nearby_characters = nearbyCharNames,
            available_objects = GetObjectsInSpace(spaceName)
        },
        global_context = new {
            time = GameTime.current,
            day = GameTime.dayNumber,
            weather = Weather.current
        }
    });

    // 4. Execute AI's decision
    ExecuteAction(character, decision.action);
}
```

### Executing AI Actions

```csharp
void ExecuteAction(Character character, Action action) {
    switch (action.actionType) {
        case "move":
            var destination = action.props["destination"];
            var destinationType = action.props["destination_type"]; // "place", "object", or "person"
            character.MoveTo(FindLocation(destination));
            break;

        case "initiate_conversation":
            var targetName = action.props["target_character"];
            var targetChar = FindCharacterByName(targetName);
            StartConversation(character, targetChar);
            break;

        case "use_object":
            var objectName = action.props["object_name"];
            UseObject(character, objectName);
            break;

        case "wait":
            character.Wait(5f);
            break;

        case "continue":
            // Keep doing current activity
            break;
    }
}
```

### Conversation System

```csharp
async void StartConversation(Character char1, Character char2) {
    // Start session
    var session = await POST("/interaction-sessions/", new {
        character_ids = new[] { char1.id, char2.id },
        interaction_type = "dialog"
    });

    // Lock characters
    char1.isInteracting = true;
    char2.isInteracting = true;

    // Show UI
    ShowConversationBubble(char1, char2);

    // Auto-advance conversation
    StartCoroutine(ConversationLoop(session.id));
}

IEnumerator ConversationLoop(string sessionId) {
    for (int i = 0; i < 6; i++) {  // 6 messages max
        yield return new WaitForSeconds(3f);

        var response = await POST($"/interaction-sessions/{sessionId}/advance");
        var lastMsg = response.messages[response.messages.Count - 1];

        ShowDialogue(lastMsg.character_name, lastMsg.content);
    }

    // End conversation
    await POST($"/interaction-sessions/{sessionId}/end");
    HideConversationBubble();
    char1.isInteracting = false;
    char2.isInteracting = false;
}
```

---

## 📊 Data Models

### Character

```json
{
  "_id": "...",
  "name": "Marcus Blackwood",
  "age": 16,
  "race": "Black",
  "gender": "Male",
  "occupation": "Student",
  "background": "The middle Blackwood child...",
  "personality_traits": [
    "ambition: high",
    "confrontational: medium",
    "sociable: high",
    "core_motivation: escape this small town and find adventure",
    "impulsive", "brave", "insecure"
  ],
  "appearance": {
    "hair": 4,
    "shoes": 1,
    "bottom": 3,
    "top": 7
  },
  "position": {
    "x": 0.0,
    "y": 0.0
  },
  "needs": {
    "happiness": 55,
    "energy": 80,
    "hunger": 70,
    "hygiene": 50,
    "anger": 30,
    "sadness": 40
  },
  "current_desire": "find Isabella and talk to her",
  "action_log": [...],
  "memory_log": [...],
  "relationships": ["char_id_1", "char_id_2"]
}
```

### Bidirectional Relationship

```json
{
  "_id": "...",
  "character_id_1": "marcus_id",
  "character_id_2": "isabella_id",

  "char1_relationship_type": "Romantic",
  "char1_summary": "Has an intense crush on her",
  "char1_score": 80,
  "char1_interaction_history": [...],

  "char2_relationship_type": "Friendly",
  "char2_summary": "Finds him annoying but amusing",
  "char2_score": 45,
  "char2_interaction_history": [...],

  "current_interaction_state": "none"
}
```

**Key Point:** Single document, different perspectives. Marcus likes Isabella (80) more than Isabella likes Marcus (45).

---

## 🧠 How AI Works

### Decision Making

1. Unity calls `.decide()` with current context
2. Backend gathers: personality, needs, memories, relationships
3. Claude AI analyzes and decides action
4. Returns: state changes + action to execute
5. Unity executes the action

### Conversations

1. Characters start talking (Unity or AI triggered)
2. Backend auto-creates relationships if first meeting
3. AI generates realistic dialogue turn-by-turn
4. When ending: AI summarizes and updates relationships
5. Each character can feel differently about the same conversation

### Relationships

-   Bidirectional: Single document, two perspectives
-   Asymmetric: Scores can be very different
-   Auto-updating: Conversations change scores
-   Memory-linked: Interaction histories tracked

---

## 🔧 Environment Variables

```env
MONGO_DB_URI=mongodb://localhost:27017/ai_life_sim
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 📚 Character Generation

Generate diverse, interconnected characters:

```bash
python generate_characters.py  # Uses Claude to generate 20 characters
python load_to_mongo.py        # Loads into MongoDB
```

**Generates:**

-   20 unique characters with medieval occupations
-   Complex family relationships
-   Varied personalities with decision-guiding traits
-   Bidirectional relationship network
-   Appearance asset codes for Unity sprites

---

## 🎯 Key Endpoints Summary

| Endpoint                             | Method | Purpose                      |
| ------------------------------------ | ------ | ---------------------------- |
| `/characters`                        | GET    | Load all characters          |
| `/characters/{id}`                   | GET    | Get character state          |
| `/characters/save-positions`         | POST   | Save all character positions |
| `/characters/{id}/decide`            | POST   | AI decision-making           |
| `/characters/{id}/use/{object}`      | POST   | Object interaction           |
| `/relationships/character/{id}`      | GET    | Get relationships            |
| `/context/generate-space-context`    | POST   | Generate space description   |
| `/interaction-sessions/`             | POST   | Start conversation           |
| `/interaction-sessions/{id}/advance` | POST   | AI dialogue generation       |
| `/interaction-sessions/{id}/end`     | POST   | End & summarize              |

---

## 🚀 Production Deployment

### MongoDB Atlas (Cloud Database)

1. Create free cluster at mongodb.com/cloud/atlas
2. Get connection string
3. Update `MONGO_DB_URI` in `.env`

### API Hosting Options

-   **Railway** - Easy deployment, good for hackathons
-   **Render** - Free tier available
-   **Fly.io** - Global deployment

---

## 🐛 Troubleshooting

**MongoDB Connection Failed:**

-   Check `MONGO_DB_URI` in `.env`
-   Ensure MongoDB is running (local) or accessible (cloud)

**LLM Generation Failed:**

-   Verify `ANTHROPIC_API_KEY` is set
-   Check API key has credits
-   Check internet connection

**Character Not Found:**

-   Run `python load_to_mongo.py` to load characters
-   Check MongoDB has data

---

## 📖 Documentation

-   Interactive API docs: `http://localhost:8000/docs`
-   Test endpoints with Swagger UI
-   See example requests/responses

---

## 🎭 Example: Marcus's Day in Unity

```
1. Game starts → Unity loads Marcus from /characters
2. Unity spawns Marcus at Residential District
3. Unity calls Marcus.decide("character spawned")
   → AI returns: {action: {actionType: "move", props: {destination: "Town Square", destination_type: "place"}}}
4. Unity moves Marcus to Town Square
5. Unity calls /context/generate-space-context
   → AI returns: "Marcus is looking around. Isabella is at her stall."
6. Unity calls Marcus.decide("arrived at new location")
   → AI sees Isabella nearby (crush, score 80)
   → AI returns: {action: {actionType: "initiate_conversation", props: {target_character: "Isabella Cortez"}}}
7. Unity starts conversation between Marcus & Isabella
8. Unity calls /advance every 3 seconds
   → AI Marcus: "Hey Isabella!"
   → AI Isabella: "Marcus, I'm working..."
9. After 4-6 messages, Unity calls /end
   → AI analyzes conversation
   → Updates: Marcus→Isabella +3, Isabella→Marcus -1
   → Both get memories
10. Characters unlocked, cycle continues
```

---

## 🏗️ Architecture

```
Unity Game (C#)
    ↓ HTTP/REST
FastAPI Backend (Python)
    ↓
MongoDB (Character Data)
    ↓
Claude 4.5 Sonnet (AI Brain)
```

---

## 📝 License

Built for Hack Western hackathon project.

---

## 🎉 Ready for Unity!

All systems implemented and tested. Just plug into Unity with UnityWebRequest and start building your AI life simulation! 🎮
