# Love Island 🏝️💕

An AI-powered social simulation where autonomous agents live, interact, and create drama on a virtual island.

## Inspiration

We were fascinated by the idea of creating a digital petri dish for human-like social interactions. Inspired by reality TV shows like Love Island and The Sims' autonomous behavior systems, we wanted to explore what happens when you give AI agents personalities, desires, and the freedom to interact naturally. What kind of relationships would form? What drama would unfold? Could AI create compelling narratives without human scripting?

## What it does

Love Island is a real-time social simulation where AI-controlled characters autonomously navigate an island environment, making their own decisions about who to talk to, who to pursue romantically, and even who to fight. Each character has unique traits and memories that influence their behavior.

**Key Features:**
- **Autonomous Decision Making**: Characters use AI to decide their next actions based on their surroundings, nearby characters, and personal history
- **Dynamic Interactions**: Characters can talk, flirt, kiss, fight, and interact with objects in the environment
- **Spatial Awareness**: Characters detect when they enter different spaces (beach, villa, pool) and react to who's around them
- **Proximity-Based Events**: When characters get close to each other, new social dynamics trigger
- **Expressive Communication**: Speech bubbles with smooth animations show what characters are saying
- **Realistic Movement**: Characters pathfind to targets and automatically face who they're interacting with

## How we built it

- **Unity** for the 3D simulation environment, character animations, and NavMesh pathfinding
- **Python backend** server that hosts the AI decision-making engine
- **RESTful API** connecting the Unity frontend to AI models for real-time character decisions
- **Custom behavior system** with coroutines handling complex multi-step actions like approaching a character and initiating interaction
- **Spatial detection system** using Physics.OverlapSphere for space and proximity awareness
- **Animator state machine** managing walking, running, talking, fighting, kissing, and other character states

## Challenges we ran into

- **Animation Priority Conflicts**: Getting walking animations to always override action animations during movement required careful state management and explicit animation clearing
- **Moving Target Tracking**: Characters needed to follow other moving characters, requiring periodic destination updates while maintaining smooth behavior
- **Action Coordination**: Ensuring that starting a new action properly cancels the previous one without visual glitches
- **AI Response Integration**: Parsing AI decisions and translating them into believable character behaviors in real-time
- **Proximity Detection Balance**: Finding the right detection radii so characters notice each other naturally without overwhelming the AI with triggers

## Accomplishments that we're proud of

- Characters genuinely feel alive - they make decisions that create emergent narratives we didn't script
- Smooth transition system between movement and interaction states
- The speech bubble system adds personality and lets you follow the drama
- Robust action system that handles edge cases like targets moving away mid-interaction
- Clean architecture separating AI decisions from behavior execution

## What we learned

- Emergent behavior is more compelling than scripted events - the AI creates stories we never anticipated
- State management in game animation is harder than it looks; priority systems are essential
- Coroutines are powerful for managing complex, multi-frame game behaviors
- The gap between "AI makes a decision" and "character believably performs it" requires significant engineering
- Social simulation is as much about the small details (facing someone when talking) as the big features

## What's next for Love Island

- **Expanded AI Personalities**: Deeper character traits, memories of past interactions, and relationship tracking
- **More Locations**: Additional island spaces with unique interaction possibilities
- **Group Dynamics**: Support for multi-character conversations and alliances
- **Viewer Mode**: Let users watch the drama unfold with camera controls and character focus
- **Voting System**: Allow viewers to influence events, just like the real show
- **Narrative Arcs**: AI-generated storylines that build over time with dramatic peaks
- **Multiplayer Spectating**: Watch the island together with friends and discuss the drama in real-time
