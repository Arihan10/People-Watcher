// Character.cs
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public class Character : MonoBehaviour
{
    [Header("Identity")]
    public string characterId;
    public GameManager.CharacterData characterData;

    [Header("Detection")]
    public float detectionRadius = 6f;
    public float proximityRadius = 3f;

    [Header("Current State")]
    [SerializeField] private string currentDesire;
    [SerializeField] private string lastThought;
    [SerializeField] private string currentAction;
    [SerializeField] private string currentSpace;

    [Header("Needs")]
    [Range(0, 100)] [SerializeField] private int happiness = 70;
    [Range(0, 100)] [SerializeField] private int energy = 100;
    [Range(0, 100)] [SerializeField] private int hunger = 30;
    [Range(0, 100)] [SerializeField] private int hygiene = 80;
    [Range(0, 100)] [SerializeField] private int health = 100;

    [Header("Feelings")]
    [Range(0, 100)] [SerializeField] private int anger = 0;
    [Range(0, 100)] [SerializeField] private int sadness = 0;
    [Range(0, 100)] [SerializeField] private int excitement = 20;
    [Range(0, 100)] [SerializeField] private int fear = 0;
    [Range(0, 100)] [SerializeField] private int love = 0;

    [Header("Decision State")]
    [SerializeField] private bool isInInteraction;
    [SerializeField] private string activeSessionId;

    [Header("Recent Activity")]
    [SerializeField] private List<string> recentTriggers = new List<string>();
    [SerializeField] private List<string> recentActions = new List<string>();

    // Private state
    List<Space> currentSpaces = new List<Space>();
    CharacterBehaviour characterBehaviour;
    List<Character> nearbyCharacters = new List<Character>();
    const int MAX_HISTORY = 8;

    [System.Serializable]
    public class DecideRequest
    {
        public string trigger_source;
        public int priority;
        public string session_id;
        public SpaceState[] space_states;
        public GameManager.GlobalContext global_context;
    }

    [System.Serializable]
    public class SpaceState
    {
        public string space_name;
        public string description;
        public string[] characters_present;
        public string[] available_objects;
    }

    void Start()
    {
        if (string.IsNullOrEmpty(characterId))
            characterId = name.ToLower().Replace(" ", "_");
        characterBehaviour = GetComponent<CharacterBehaviour>();
    }

    /// <summary>
    /// Initialize runtime state from loaded character data.
    /// Called by GameManager after instantiation.
    /// </summary>
    public void InitializeState()
    {
        if (characterData == null) return;

        currentDesire = characterData.current_desire;

        // Initialize needs
        if (characterData.needs != null)
        {
            happiness = characterData.needs.happiness;
            energy = characterData.needs.energy;
            hunger = characterData.needs.hunger;
            hygiene = characterData.needs.hygiene;
            health = characterData.needs.health;
        }
    }

    /// <summary>
    /// Update interaction state (called by DecisionManager).
    /// </summary>
    public void SetInteractionState(bool inInteraction, string sessionId = null)
    {
        isInInteraction = inInteraction;
        activeSessionId = sessionId;
    }

    void Update()
    {
        // Handle space detection
        Collider[] overlaps = Physics.OverlapSphere(transform.position, detectionRadius);
        List<Space> newSpaces = new List<Space>();

        foreach (Collider col in overlaps)
        {
            Space space = col.GetComponent<Space>();
            if (space != null && col.isTrigger)
            {
                newSpaces.Add(space);
            }
        }

        foreach (Space space in newSpaces)
        {
            if (!currentSpaces.Contains(space))
            {
                currentSpaces.Add(space);
                space.AddCharacter(this);
                GameManager.Instance.UpdateCharacterLocation(this, space.spaceName);
                OnEnterSpace(space);
            }
        }

        foreach (Space space in currentSpaces.ToList())
        {
            if (!newSpaces.Contains(space))
            {
                currentSpaces.Remove(space);
                space.RemoveCharacter(this);
                if (currentSpaces.Count == 0)
                {
                    GameManager.Instance.UpdateCharacterLocation(this, null);
                    currentSpace = "";
                }
                else
                {
                    GameManager.Instance.UpdateCharacterLocation(this, currentSpaces[0].spaceName);
                    currentSpace = currentSpaces[0].spaceName;
                }
            }
        }

        // Handle character proximity detection
        Collider[] proximityOverlaps = Physics.OverlapSphere(transform.position, proximityRadius);
        List<Character> newNearbyCharacters = new List<Character>();

        foreach (Collider col in proximityOverlaps)
        {
            Character otherCharacter = col.GetComponent<Character>();
            if (otherCharacter != null && otherCharacter != this)
            {
                newNearbyCharacters.Add(otherCharacter);
            }
        }

        foreach (Character character in newNearbyCharacters)
        {
            if (!nearbyCharacters.Contains(character))
            {
                nearbyCharacters.Add(character);
                AddDecide($"you are in close proximity to {character.name}");
            }
        }

        foreach (Character character in nearbyCharacters.ToList())
        {
            if (!newNearbyCharacters.Contains(character))
            {
                nearbyCharacters.Remove(character);
            }
        }
    }

    void OnEnterSpace(Space space)
    {
        currentSpace = space.spaceName;
        AddDecide("Just entered space " + space.spaceName);
    }

    public void AddDecide(string triggerSource, DecisionManager.DecisionPriority priority = DecisionManager.DecisionPriority.Normal)
    {
        // Track the trigger
        recentTriggers.Insert(0, triggerSource);
        if (recentTriggers.Count > MAX_HISTORY)
            recentTriggers.RemoveAt(recentTriggers.Count - 1);

        if (DecisionManager.Instance != null)
            DecisionManager.Instance.QueueDecision(this, triggerSource, priority);
    }

    /// <summary>
    /// Track an action that was executed.
    /// </summary>
    public void TrackAction(string actionDescription)
    {
        currentAction = actionDescription;
        recentActions.Insert(0, actionDescription);
        if (recentActions.Count > MAX_HISTORY)
            recentActions.RemoveAt(recentActions.Count - 1);
    }

    public IEnumerator Decide(string triggerSource, int priority = 1)
    {
        var spaceStates = currentSpaces.Select(space => new SpaceState
        {
            space_name = space.spaceName,
            description = space.spaceDescription,
            characters_present = space.GetCharacterNames(),
            available_objects = space.GetInteractableNames()
        }).ToArray();

        var request = new DecideRequest
        {
            trigger_source = triggerSource,
            priority = priority,
            session_id = null,
            space_states = spaceStates,
            global_context = GameManager.Instance.GetGlobalContext()
        };

        string json = JsonConvert.SerializeObject(request);
        string url = $"http://localhost:8000/characters/{characterId}/decide";

        using (UnityWebRequest www = UnityWebRequest.Post(url, json, "application/json"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                ProcessDecisionResponse(www.downloadHandler.text);
            }
        }
    }
    
    public IEnumerator DecideInInteraction(string sessionId, string context)
    {
        var spaceStates = currentSpaces.Select(space => new SpaceState
        {
            space_name = space.spaceName,
            description = space.spaceDescription,
            characters_present = space.GetCharacterNames(),
            available_objects = space.GetInteractableNames()
        }).ToArray();

        var request = new DecideRequest
        {
            trigger_source = context,
            priority = 2, // High priority for interaction turns
            session_id = sessionId,
            space_states = spaceStates,
            global_context = GameManager.Instance.GetGlobalContext()
        };

        string json = JsonConvert.SerializeObject(request);
        string url = $"http://localhost:8000/characters/{characterId}/decide";

        using (UnityWebRequest www = UnityWebRequest.Post(url, json, "application/json"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                ProcessDecisionResponse(www.downloadHandler.text);
            }
        }
    }

    /// <summary>
    /// Find a character by their characterId.
    /// </summary>
    public static Character FindCharacterById(string characterId)
    {
        var characters = FindObjectsByType<Character>(FindObjectsSortMode.None);
        return System.Array.Find(characters, c => c.characterId == characterId);
    }
    
    /// <summary>
    /// Find a character by their display name.
    /// </summary>
    public static Character FindCharacterByName(string charName)
    {
        var go = GameObject.Find(charName);
        return go?.GetComponent<Character>();
    }


    void ProcessDecisionResponse(string jsonResponse)
    {
        var response = JObject.Parse(jsonResponse);
        string status = response["status"]?.ToString();
        string responseSessionId = response["session_id"]?.ToString();
        
        // Handle error cases
        if (status == "target_unavailable")
        {
            DecisionManager.Instance.QueueDecision(this, "target was busy", DecisionManager.DecisionPriority.Normal);
            return;
        }
        
        if (status == "already_in_interaction")
        {
            // Ignore - we're already in the interaction, await turn trigger
            return;
        }
        
        // STALE RESPONSE DETECTION:
        // If we're currently in an interaction but this response has no session_id,
        // it's a stale non-interaction response that started before the interaction.
        // Discard it to prevent executing inappropriate actions (like "move") during conversation.
        if (isInInteraction && string.IsNullOrEmpty(responseSessionId))
        {
            Debug.Log($"[DECISION] Discarding stale non-interaction response for {name} (now in interaction)");
            return;
        }
        
        // If response has a session_id AND we're already in a DIFFERENT session,
        // this is from a stale/different interaction - discard it.
        // NOTE: We must check that activeSessionId is also set, otherwise we'd discard
        // the response that CREATES our interaction (when we're the initiator).
        if (!string.IsNullOrEmpty(responseSessionId) && 
            !string.IsNullOrEmpty(activeSessionId) && 
            responseSessionId != activeSessionId)
        {
            Debug.Log($"[DECISION] Discarding response for wrong session {ShortSessionId(responseSessionId)} (active: {ShortSessionId(activeSessionId)})");
            return;
        }

        // Extract and store inner thought
        string thought = response["inner_thought"]?.ToString();
        if (!string.IsNullOrEmpty(thought))
            lastThought = thought;

        // Apply state changes to local state
        ApplyStateChanges(response["state_changes"] as JObject);
        
        // Extract action info
        string actionType = response["action"]?["actionType"]?.ToString();
        if (string.IsNullOrEmpty(actionType)) return;
        
        JObject props = response["action"]["props"] as JObject;
        string sessionId = response["session_id"]?.ToString();
        string nextTurn = response["next_turn"]?.ToString();

        // Build action description for tracking
        string actionDesc = BuildActionDescription(actionType, props);
        TrackAction(actionDesc);
        
        // Execute the action via ActionExecutor
        ActionExecutor.Instance.Execute(this, actionType, props, sessionId);
        
        // Handle turn triggering for interactions
        // This is the SINGLE path for all turn triggers (including after initiate_interaction)
        if (!string.IsNullOrEmpty(nextTurn) && !string.IsNullOrEmpty(sessionId))
        {
            Character nextChar = ActionExecutor.Instance.FindCharacter(nextTurn);
            if (nextChar != null)
            {
                // Build context appropriate to the action type
                string context = actionType switch
                {
                    "speak_in_interaction" => $"{name} said: \"{props["dialogue"]}\"",
                    "initiate_interaction" => $"{name} said: \"{props["opening"]}\"",
                    "fight_action" => $"{name} {props["action"]}s you!",
                    "romance_action" => $"{name} {props["action"]}s you!",
                    _ => $"{name} performed {actionType}"
                };
                
                // Calculate delay based on action type (reading time + thinking pause)
                float delay = CalculateTurnDelay(actionType, props);
                
                Debug.Log($"[INTERACTION] {name} triggering {nextChar.name}'s turn in session {ShortSessionId(sessionId)} (delay: {delay:F1}s)");
                
                if (delay > 0)
                {
                    StartCoroutine(DelayedTurnTrigger(nextChar, sessionId, context, delay));
                }
                else
                {
                    InteractionHandler.Instance.TriggerInteractionTurn(nextChar, sessionId, context);
                }
            }
            else
            {
                Debug.LogError($"[INTERACTION ERROR] Could not find next character '{nextTurn}' for session {ShortSessionId(sessionId)}. Turn will not be triggered!");
            }
        }
    }
    
    /// <summary>
    /// Calculate the delay before triggering the next character's turn.
    /// Includes reading time for dialogue plus a thinking pause.
    /// </summary>
    float CalculateTurnDelay(string actionType, JObject props)
    {
        const float POST_SPEECH_BUFFER = 1.0f;  // Animation-out (0.25s) + thinking pause (0.75s)
        const float ACTION_PAUSE = 2.5f;        // For fight/romance animation time + pause
        
        // Get dialogue text based on action type
        string text = actionType switch
        {
            "speak_in_interaction" => props?["dialogue"]?.ToString(),
            "initiate_interaction" => props?["opening"]?.ToString(),
            _ => null
        };
        
        // For dialogue-based actions, calculate reading time
        if (text != null)
        {
            int wordCount = text.Split(new[] { ' ', '\n', '\r' }, System.StringSplitOptions.RemoveEmptyEntries).Length;
            float readingTime = Mathf.Clamp(wordCount * 0.2f + 0.5f, 2.0f, 9.0f);
            return readingTime + POST_SPEECH_BUFFER;
        }
        
        // For fight/romance actions, use fixed animation pause
        if (actionType == "fight_action" || actionType == "romance_action")
        {
            return ACTION_PAUSE;
        }
        
        // No delay for other actions
        return 0f;
    }
    
    /// <summary>
    /// Trigger the next character's turn after a delay.
    /// Validates that the session is still active before triggering.
    /// </summary>
    IEnumerator DelayedTurnTrigger(Character nextChar, string sessionId, string context, float delay)
    {
        yield return new WaitForSeconds(delay);
        
        // Verify session is still active before triggering
        // Check both our local state AND the InteractionHandler's session tracking
        bool sessionStillActive = (isInInteraction && activeSessionId == sessionId) ||
                                   InteractionHandler.Instance.IsSessionActive(sessionId);
        
        if (sessionStillActive)
        {
            InteractionHandler.Instance.TriggerInteractionTurn(nextChar, sessionId, context);
        }
        else
        {
            Debug.Log($"[INTERACTION] Delayed turn cancelled - session {ShortSessionId(sessionId)} no longer active");
        }
    }

    void ApplyStateChanges(JObject stateChanges)
    {
        if (stateChanges == null) return;

        // Update desire
        string newDesire = stateChanges["current_desire"]?.ToString();
        if (!string.IsNullOrEmpty(newDesire))
            currentDesire = newDesire;

        // Update feelings
        var feelings = stateChanges["feelings"] as JObject;
        if (feelings != null)
        {
            if (feelings["anger"] != null) anger = Mathf.Clamp((int)feelings["anger"], 0, 100);
            if (feelings["sadness"] != null) sadness = Mathf.Clamp((int)feelings["sadness"], 0, 100);
            if (feelings["excitement"] != null) excitement = Mathf.Clamp((int)feelings["excitement"], 0, 100);
            if (feelings["fear"] != null) fear = Mathf.Clamp((int)feelings["fear"], 0, 100);
            if (feelings["love"] != null) love = Mathf.Clamp((int)feelings["love"], 0, 100);
        }

        // Update needs (these are deltas from the API)
        var needs = stateChanges["needs"] as JObject;
        if (needs != null)
        {
            if (needs["happiness"] != null) happiness = Mathf.Clamp(happiness + (int)needs["happiness"], 0, 100);
            if (needs["energy"] != null) energy = Mathf.Clamp(energy + (int)needs["energy"], 0, 100);
            if (needs["hunger"] != null) hunger = Mathf.Clamp(hunger + (int)needs["hunger"], 0, 100);
            if (needs["hygiene"] != null) hygiene = Mathf.Clamp(hygiene + (int)needs["hygiene"], 0, 100);
            if (needs["health"] != null) health = Mathf.Clamp(health + (int)needs["health"], 0, 100);
        }
    }

    string BuildActionDescription(string actionType, JObject props)
    {
        return actionType switch
        {
            "move" => $"move → {props?["destination"]}",
            "use_object" => $"use {props?["object_name"]}",
            "speak" => $"say: \"{TruncateText(props?["dialogue"]?.ToString(), 30)}\"",
            "initiate_interaction" => $"talk to {props?["target_character"]}",
            "speak_in_interaction" => $"say: \"{TruncateText(props?["dialogue"]?.ToString(), 30)}\"",
            "fight_action" => $"fight: {props?["action"]}",
            "romance_action" => $"romance: {props?["action"]}",
            "leave_interaction" => "leave conversation",
            "none" => "idle",
            _ => actionType
        };
    }

    string TruncateText(string text, int maxLength)
    {
        if (string.IsNullOrEmpty(text)) return "";
        return text.Length <= maxLength ? text : text.Substring(0, maxLength) + "...";
    }
    
    /// <summary>
    /// Safely get a short version of a session ID for logging.
    /// </summary>
    public static string ShortSessionId(string sessionId)
    {
        if (string.IsNullOrEmpty(sessionId)) return "null";
        return sessionId.Length >= 8 ? sessionId.Substring(0, 8) : sessionId;
    }
}