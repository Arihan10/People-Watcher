# AI Village Simulator - Complete Setup Guide

## Overview

This is a complete AI-powered village simulation where characters make autonomous decisions, interact with each other, and form relationships using Claude Sonnet 4.

## Architecture

- **Backend**: Python FastAPI with MongoDB for data storage and Claude Sonnet for decision-making
- **Frontend**: Unity with C# scripts for character behavior, movement, and animations
- **Communication**: REST API between Unity and Python backend

## Prerequisites

1. **Unity** (already installed based on your project)
2. **Python 3.9+**
3. **MongoDB** (local or Atlas)
4. **Anthropic API Key** (for Claude Sonnet)

## Backend Setup

### Step 1: Install Python Dependencies

```bash
cd api
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the `api` directory:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
MONGO_URI=mongodb://localhost:27017/village_sim
```

**Get your Anthropic API key:**
- Sign up at https://console.anthropic.com/
- Create an API key in your account settings

**MongoDB options:**
- **Local:** Install from https://www.mongodb.com/try/download/community
- **Docker:** `docker run -d -p 27017:27017 --name mongodb mongo:latest`
- **Cloud (Atlas):** Use a connection string from https://www.mongodb.com/cloud/atlas

### Step 3: Generate Initial Characters

This populates the database with 10 characters and their relationships:

```bash
python generate_characters.py
```

You should see output like:
```
Generating 10 characters...
  Created character: Timmy
  Created character: Sarah
  ...
Generated 10 characters successfully!

Generating relationships...
  Created relationship: Sarah & Timmy
  ...
Generated 15 relationships successfully!

Database populated! Ready to run the simulation.
```

### Step 4: Start the Backend Server

```bash
python main.py
```

The API will start on `http://localhost:8000`

Verify it's running by visiting `http://localhost:8000/docs` - you should see the API documentation.

## Unity Setup

### Step 1: Add New Components to Scene

The new Unity scripts need to be added to your scene:

1. **DecisionManager**: Create an empty GameObject named "DecisionManager" and add the `DecisionManager.cs` script
2. **InteractionHandler**: Create an empty GameObject named "InteractionHandler" and add the `InteractionHandler.cs` script
3. **ActionExecutor**: Create an empty GameObject named "ActionExecutor" and add the `ActionExecutor.cs` script

These should be at the same level as your existing GameManager.

### Step 2: Verify Character Prefab

Make sure your character prefab has these components:
- `Character.cs` (already there)
- `CharacterBehaviour.cs` (already there)
- `CharacterAppearance.cs` (already there)
- `NavMeshAgent` (already there)
- `Animator` (already there)

### Step 3: Run Unity

1. Make sure the backend API is running (`python main.py` in the `api` folder)
2. Press Play in Unity
3. GameManager will automatically load characters from the API and spawn them

## How It Works

### Decision Flow

1. **Triggers**: Characters detect events (entering spaces, proximity to others, etc.)
2. **Queue**: DecisionManager queues decisions per-character (up to 5 concurrent)
3. **API Call**: Unity sends context to `/characters/{id}/decide`
4. **LLM Decision**: Backend uses Claude to decide what the character should do
5. **Action Execution**: ActionExecutor performs the action (move, talk, interact, etc.)
6. **Activity Sync**: Unity notifies backend of activity changes

### Interaction Flow

1. **Initiation**: Character A decides to talk to Character B
2. **Session Creation**: Backend atomically locks both characters
3. **Turn-Based**: Characters take turns speaking/acting
4. **Turn Triggering**: Each response includes `next_turn` to trigger the other character
5. **Completion**: When someone leaves, backend summarizes and stores in relationship history

### Concurrency

- **Per-Character Queues**: Each character has their own decision queue
- **Global Limit**: Maximum 5 concurrent API calls
- **Priority System**: Low/Normal/High/Critical (Critical can interrupt interactions)
- **Interaction Locks**: Characters in interactions ignore normal triggers

## Customization

### Adding More Characters

Re-run the generation script with a different number:

Edit `generate_characters.py` and change:
```python
asyncio.run(generate_village(num_characters=20))  # Change from 10 to 20
```

### Modifying Character Behavior

The decision-making logic is in the LLM prompt. Edit `app/services/llm_service.py` in the `_build_decide_prompt` method to adjust how characters think.

### Adding New Action Types

1. Add to `ActionType` enum in `app/models/requests.py`
2. Add case in `ActionExecutor.Execute()` in Unity
3. Update the LLM prompt to include the new action

## Troubleshooting

### Backend won't start

- **Error: "ANTHROPIC_API_KEY not found"**
  - Make sure `.env` file exists in the `api` directory
  - Check the API key is correct

- **Error: "Cannot connect to MongoDB"**
  - Make sure MongoDB is running
  - Check the `MONGO_URI` in `.env`
  - Try: `mongodb://localhost:27017/village_sim` for local

### Unity can't connect to backend

- **Error: "Connection refused"**
  - Make sure the backend is running (`python main.py`)
  - Check it's on `http://localhost:8000`
  - Try accessing `http://localhost:8000` in your browser

- **Error: "No characters loaded"**
  - Run `python generate_characters.py` to populate the database
  - Check the backend logs for errors

### Characters not moving/acting

- **Check Unity Console** for errors
- **Check Backend Logs** for LLM errors
- **Verify**: DecisionManager, InteractionHandler, and ActionExecutor are in the scene
- **Verify**: Character prefab has all required components

## Development

### Running Tests

```bash
cd api
pytest  # If tests are added
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### Database Inspection

Use MongoDB Compass or mongo shell to inspect the database:

```bash
mongo village_sim
db.characters.find().pretty()
db.relationships.find().pretty()
db.interaction_sessions.find().pretty()
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        UNITY                             │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────┐    │
│  │ Character  │  │ Decision     │  │ Action      │    │
│  │ (triggers) │─▶│ Manager      │─▶│ Executor    │    │
│  └────────────┘  │ (queue)      │  │ (execute)   │    │
│                  └──────────────┘  └─────────────┘    │
│                         │                               │
│                         ▼ HTTP POST                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                     │
│  ┌──────────────┐  ┌──────────┐  ┌────────────┐       │
│  │ Character    │  │ Claude   │  │ MongoDB    │       │
│  │ Routes       │─▶│ Sonnet   │─▶│ (state)    │       │
│  └──────────────┘  └──────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## What Was Implemented

### Backend (Python)
✅ MongoDB connection with Motor (async)
✅ Pydantic models for all data structures
✅ LLM service with Claude Sonnet 4
✅ Character service (CRUD, state management)
✅ Relationship service (adjacency list operations)
✅ Interaction service (session management, atomic locking)
✅ Space service (context generation)
✅ Character routes (GET, POST /decide, POST /activity)
✅ Context routes (POST /generate-space-context)
✅ Interaction routes (GET /active, POST /end)
✅ Character generation script

### Unity (C#)
✅ DecisionManager (per-character queues, concurrency control)
✅ InteractionHandler (session lifecycle, turn triggering)
✅ ActionExecutor (centralized action execution)
✅ Updated Character.cs (new decision flow, session support)
✅ Updated CharacterBehaviour.cs (Emote method)
✅ Updated GameManager.cs (removed old queue)

### Features Implemented
✅ Per-character decision processing (up to 5 concurrent)
✅ Priority system (Low/Normal/High/Critical)
✅ Turn-based interactions (dialog, fight, romance)
✅ Atomic session creation (race condition handling)
✅ Activity tracking and synchronization
✅ Relationship management with directional feelings
✅ Space context generation
✅ Memory and action logging
✅ State management (needs, feelings, desires)
✅ All 10 action types (move, use_object, speak, emote, etc.)

## Next Steps

1. **Run the backend** and generate characters
2. **Open Unity** and ensure the new components are in the scene
3. **Press Play** and watch your AI village come to life!
4. **Observe** characters making decisions, talking to each other, and interacting

The characters will:
- Walk around the village
- Notice and react to their environment
- Start conversations with each other
- Remember significant events
- Develop and change relationships over time
- Make decisions based on their personalities and current state

Enjoy your AI village simulation!
