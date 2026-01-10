# Unity Simulation Frontend

Minimal simulation that demonstrates how Unity will interact with the backend.

## What This Is

This is **NOT** the final UI. This simulates the **backend integration flow** that Unity will implement.

## What It Shows

### 4 Characters (Focused Subset)
- Marcus Blackwood (16, Student) - Has crush on Isabella
- Isabella Cortez (17, Merchant) - Ambitious, focused on work
- Thomas Blackwood (22, Blacksmith) - Gentle, romantic
- Elena Blackwood (19, Tailor) - Creative, anxious

### 3 Spaces
- Town Square (fountain, bench, notice_board)
- The Sleeping Dragon Inn (bar, fireplace, tables)
- Blackwood Forge (anvil, forge, hammer)

## How It Works

### Unity Simulation Loop

Every tick (3 seconds default):

1. **If conversation is active:**
   - Advance conversation (AI generates dialogue)
   - Display in log
   - End after 5 messages

2. **Else - Character makes decision:**
   - Generate space context from characters present
   - Call `.decide()` with full context
   - AI returns action (move/talk/use/wait)
   - Execute action
   - Log everything

### What You'll See

```
🎯 Marcus Blackwood's Turn
   Location: Town Square
   Desire: find Isabella and talk to her
   Happiness: 55/100, Energy: 80/100
   📍 Scene: "Marcus is looking around the square."
   🧠 AI Decision: Saw Isabella nearby and wants to spend time with her
   📤 Action: initiate_conversation
   💬 Started conversation: Marcus Blackwood & Isabella Cortez

💬 Marcus: "Hey Isabella! I've been looking for you."
💬 Isabella: "Marcus, I'm working on inventory right now."
💬 Marcus: "Can I help? We could work together!"
💬 Isabella: "You're persistent. Fine, but stay focused."
✅ Conversation ended - relationships updated

🎯 Isabella Cortez's Turn
   Location: Town Square
   Desire: finish inventory and get back to work
   📍 Scene: "Marcus is standing nearby. Isabella is at the notice board."
   🧠 AI Decision: Conversation took time, needs to get back to work
   📤 Action: move
   🚶 Isabella → Cortez Trading Company
```

## Setup

```bash
cd frontend
npm install
npm run dev
```

Visit: http://localhost:3000

## Key Features

### Predictable & Clear
- Only 4 characters (easy to track motivations)
- Only 3 spaces (see movement patterns)
- Detailed logging (every decision explained)
- Turn-based (one character at a time)

### Exactly Like Unity
- Generates space context before decisions
- AI decides based on full context
- Returns action object
- Executes action
- Conversations work the same way

### Shows AI Behavior
- Watch Marcus chase Isabella (crush motivation)
- See Isabella prioritize work (ambitious trait)
- Thomas focused on blacksmithing (occupation-driven)
- Elena's creative desires

## This is YOUR UNITY INTEGRATION BLUEPRINT

Copy this logic to Unity C# and you're done!


