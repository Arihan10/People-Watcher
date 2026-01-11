# Diagnostics & Troubleshooting

## First: Fix the Anthropic Error

Before anything else, run:
```bash
pip install --upgrade anthropic
```

Then restart the backend. Without this, nothing will work.

---

## Comprehensive Logging System

A detailed logging system has been implemented that tracks every decision, action, and state change.

### Where to Find Logs

**Backend Logs:** `api/logs/session_YYYYMMDD_HHMMSS.log`

A new log file is created each time Unity connects (GET /characters is called).

### What Gets Logged

Every log entry shows:
```
[HH:MM:SS.mmm] +elapsed_seconds | CATEGORY
  Description
  {structured_data}
```

**Categories:**
- `UNITY CONNECTED` - Unity connected and requested characters
- `CHARACTERS LOADED` - Characters loaded from database
- `DECISION REQUEST` - Character making a decision (includes trigger, priority)
- `MODE` - Whether processing in NORMAL or INTERACTION mode
- `LLM CALL` - LLM response summary
- `ACTION EXECUTED` - Action being performed
- `ACTION LOGGED` - Action added to character's log
- `STATE CHANGE` - Character state updated
- `ACTIVITY UPDATE` - Character activity changed
- `INTERACTION` - Session created/ended/interrupted
- `SPACE CONTEXT` - Space description generated
- `ERROR` - Any errors

### Reading the Logs

Open the latest log file in `api/logs/` to see:

1. **Unity Connection** - Shows when the game started
2. **Character List** - Names of all loaded characters
3. **Decisions** - Each character's decision triggers
4. **LLM Responses** - What action the AI chose
5. **Actions** - What actually executed
6. **Movement** - Destinations and whether they succeeded
7. **Interactions** - Conversations starting/ending

---

## Why Characters Aren't Moving - Likely Causes

### Issue 1: LLM Not Returning Move Actions

**Check the logs for:**
```
[TIME] | LLM CALL
  decide for character_name
  Action: none, Thought: ...
```

If you see lots of `Action: none` or `Action: speak`, but no `Action: move`, the LLM isn't choosing to move.

**Causes:**
- Generic desires ("start the day") don't motivate movement
- No clear destinations shown to LLM
- Characters idle by default

**Fix:** I've updated:
- Character generation to give occupation-specific desires
- LLM prompt to show all available spaces
- Prompt to encourage active movement

**Re-generate characters:**
```bash
# Drop the old characters
mongosh village_sim --eval "db.characters.deleteMany({}); db.relationships.deleteMany({})"

# Generate new ones with better desires
python generate_characters.py
```

### Issue 2: Destinations Don't Exist in Unity

**Check Unity Console for:**
```
[MOVEMENT FAILED] No object matching 'market' found in scene
```

This means the LLM told the character to move somewhere that doesn't exist as a GameObject.

**Fix:**
- I've made movement case-insensitive and allow partial matches
- Make sure you have GameObjects in your scene named after common locations
- Examples: "Market", "Town Square", "Farm", "House", etc.

**To add destinations:**
1. Create Empty GameObject
2. Name it "Market" (or other location)
3. Characters can now move there

### Issue 3: No NavMesh

Characters need a NavMesh to walk on.

**Check:** Do you see a light blue surface in Unity Scene view when you select Navigation?

**Fix:**
1. Window → AI → Navigation
2. Select your ground plane
3. Mark as "Walkable"
4. Click "Bake"

### Issue 4: Characters Start in Interactions

If characters immediately start talking and get locked in conversations, they can't process normal movement triggers.

**Check logs for:**
```
[TIME] | INTERACTION
  CREATED | Session: abc123...
```

Right at the start of the game.

**This is actually correct behavior** if characters spawn near each other! They'll talk first, then move after.

---

## Diagnostic Steps

### 1. Check Backend Logs

```bash
# After starting game in Unity
cd api/logs
# Open the latest session_*.log file
```

Look for:
- Are decisions being made? (DECISION REQUEST entries)
- What actions is the LLM choosing? (LLM CALL entries)
- Are actions executing? (ACTION EXECUTED entries)

### 2. Check Unity Console

Look for:
- `[MOVEMENT]` - Movement succeeded
- `[MOVEMENT FAILED]` - Destination not found
- `[ACTION EXECUTOR]` - Actions being executed

### 3. Check Character Desires

In MongoDB or the logs, check what `current_desire` characters have:
- ❌ Bad: "start the day" (too generic)
- ✅ Good: "tend to the crops", "visit the market", "check on patients"

### 4. Check Available Destinations

In Unity Hierarchy, what GameObjects exist?
- If LLM says "move to market" but no "Market" GameObject exists → movement fails
- Create GameObjects for common destinations

### 5. Check NavMesh

- Is there a baked NavMesh?
- Are characters on the NavMesh?
- Check NavMeshAgent component on character prefab

---

## Expected Behavior (Once Fixed)

### Backend Logs
```
[10:30:00.123] +0.00s | UNITY CONNECTED
  Unity requested character list - Starting new session

[10:30:01.456] +1.33s | DECISION REQUEST
  Character: timmy
  {trigger: "entered Town Square", priority: 1}

[10:30:01.567] +1.44s | MODE
  timmy processing in NORMAL mode

[10:30:02.789] +2.67s | LLM CALL
  decide for timmy
  Action: move, Thought: I should check on my farm

[10:30:02.890] +2.77s | ACTION EXECUTED
  Character: timmy | Action: move
  {props: {destination: "Farm"}}
```

### Unity Console
```
[ACTION EXECUTOR] Timmy executing move with props: {"destination":"Farm"}
[MOVEMENT] Timmy moving to Farm (searched for: Farm)
```

Then you'll see the character actually walking!

---

## Quick Fixes

### Characters just standing around?
1. Re-generate with better desires: `python generate_characters.py`
2. Add destination GameObjects to Unity scene
3. Check NavMesh is baked

### Characters only talking?
- This might be correct! If they spawn near each other, they'll talk first
- Wait for conversations to end, then they'll move
- Check logs to see if they're locked in interactions

### Movement fails?
- Check Unity Console for `[MOVEMENT FAILED]` messages
- Add the missing GameObject to your scene
- Or rename existing objects to match what LLM expects

### No decisions being made?
- Check DecisionManager, InteractionHandler, ActionExecutor are in scene
- Check backend is running and responding (200 OK in logs)
- Look at backend logs for DECISION REQUEST entries

---

## Summary

**The logging system will show you exactly what's happening:**
1. What triggers are firing
2. What decisions the LLM is making
3. What actions are executing
4. Where things are failing

**Most likely issue: Movement destinations don't exist in Unity scene**

**Solution:** Create GameObjects for destinations or re-generate characters with desires matching your scene objects.
