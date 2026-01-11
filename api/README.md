# AI Village Simulator - Backend API

Backend API for the AI Village Simulator built with FastAPI, MongoDB, and Claude Sonnet.

## Setup

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `api` directory:

```env
ANTHROPIC_API_KEY=your_api_key_here
MONGO_URI=mongodb://localhost:27017/village_sim
```

### 3. Start MongoDB

Make sure MongoDB is running on your machine. If you don't have it installed:

**Windows:**
```bash
# Download from: https://www.mongodb.com/try/download/community
# Or use MongoDB Atlas (cloud): https://www.mongodb.com/cloud/atlas
```

**With Docker:**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 4. Generate Initial Characters

Run the character generation script to populate the database:

```bash
python generate_characters.py
```

This will:
- Generate 10 unique villagers with personalities and backgrounds
- Create relationships between them
- Populate the MongoDB database

### 5. Start the API Server

```bash
python main.py
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## API Endpoints

### Characters
- `GET /characters` - List all characters
- `GET /characters/{id}` - Get character details
- `POST /characters/{id}/decide` - Make a decision (core endpoint)
- `POST /characters/{id}/activity` - Update current activity

### Interactions
- `GET /interactions/active/{character_id}` - Get active session
- `POST /interactions/{session_id}/end` - Force end session

### Context
- `POST /context/generate-space-context` - Generate space description

## Architecture

```
api/
├── main.py                 # Entry point
├── generate_characters.py  # Character generation script
├── requirements.txt
├── .env
└── app/
    ├── main.py            # FastAPI app
    ├── config.py          # Settings
    ├── database.py        # MongoDB connection
    ├── models/            # Pydantic models
    ├── routes/            # API endpoints
    └── services/          # Business logic
        ├── llm_service.py          # Claude integration
        ├── character_service.py    # Character operations
        ├── relationship_service.py # Relationship operations
        ├── interaction_service.py  # Interaction sessions
        └── space_service.py        # Space context
```

## Testing

You can test the API using the interactive docs at `http://localhost:8000/docs` or with curl:

```bash
# Get all characters
curl http://localhost:8000/characters

# Test a decision
curl -X POST http://localhost:8000/characters/timmy/decide \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_source": "testing",
    "priority": 1,
    "space_states": [],
    "global_context": {
      "time": "afternoon",
      "all_spaces": [],
      "character_locations": []
    }
  }'
```

## Unity Integration

The Unity client connects to this API:
- On startup: Loads all characters via `GET /characters`
- During gameplay: Calls `POST /characters/{id}/decide` for each trigger
- Activity updates: Calls `POST /characters/{id}/activity` when characters arrive/start using objects

See the Unity scripts for implementation details:
- `DecisionManager.cs` - Per-character decision queue
- `ActionExecutor.cs` - Action execution
- `InteractionHandler.cs` - Interaction lifecycle
- `Character.cs` - Trigger detection and API calls
