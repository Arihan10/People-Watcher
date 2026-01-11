using UnityEngine;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine.Networking;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public class ActionExecutor : MonoBehaviour
{
    public static ActionExecutor Instance;
    
    // Track movement generation per character - prevents duplicate arrival notifications
    // When a new movement starts, generation increments, making any pending coroutines "stale"
    private Dictionary<Character, int> movementGeneration = new Dictionary<Character, int>();
    
    void Awake()
    {
        if (Instance == null)
            Instance = this;
        else
            Destroy(gameObject);
    }
    
    /// <summary>
    /// Main entry point - routes action response to appropriate handler
    /// </summary>
    public void Execute(Character character, string actionType, JObject props, string sessionId = null)
    {
        Debug.Log($"[ACTION EXECUTOR] {character.name} executing {actionType} with props: {props}");
        
        switch (actionType)
        {
            case "move":
                string destination = props["destination"]?.ToString();
                if (string.IsNullOrEmpty(destination))
                {
                    Debug.LogError($"[ACTION ERROR] Move action missing destination for {character.name}");
                    return;
                }
                ExecuteMove(character, destination);
                break;
            case "use_object":
                ExecuteUseObject(character, props["object_name"].ToString(), props["flavor"]?.ToString());
                break;
            case "speak":
                ExecuteSpeak(character, props["dialogue"].ToString());
                break;
            case "initiate_interaction":
                ExecuteInitiateInteraction(character, props, sessionId);
                break;
            case "speak_in_interaction":
                ExecuteSpeakInInteraction(character, props["dialogue"].ToString(), sessionId);
                break;
            case "fight_action":
                ExecuteFightAction(character, props["action"].ToString());
                break;
            case "romance_action":
                ExecuteRomanceAction(character, props["action"].ToString());
                break;
            case "leave_interaction":
                ExecuteLeaveInteraction(character, sessionId);
                break;
            case "none":
                // Do nothing - character continues current activity
                Debug.Log($"[ACTION] {character.name} chose to do nothing (continues current activity)");
                break;
            default:
                Debug.LogWarning($"[ACTION ERROR] Unknown action type: {actionType}");
                break;
        }
    }
    
    void ExecuteMove(Character c, string destination)
    {
        c.GetComponent<CharacterBehaviour>().MoveTo(destination, false);
        
        // Increment generation - any existing coroutines become stale
        int thisGeneration = IncrementMovementGeneration(c);
        StartCoroutine(WaitForArrivalAndNotify(c, destination, thisGeneration));
    }
    
    void ExecuteUseObject(Character c, string objectName, string flavor)
    {
        c.GetComponent<CharacterBehaviour>().MoveTo(objectName, false);
        
        // Same generation tracking - use_object also involves movement
        int thisGeneration = IncrementMovementGeneration(c);
        StartCoroutine(WaitForArrivalThenInteract(c, objectName, flavor, thisGeneration));
    }
    
    /// <summary>
    /// Increment and return the movement generation for a character.
    /// Used to invalidate stale arrival coroutines when a new movement starts.
    /// </summary>
    int IncrementMovementGeneration(Character c)
    {
        if (!movementGeneration.ContainsKey(c))
            movementGeneration[c] = 0;
        return ++movementGeneration[c];
    }
    
    void ExecuteSpeak(Character c, string dialogue)
    {
        // Speaking out loud, NOT in an interaction
        float duration = CalculateSpeechDuration(dialogue);
        c.GetComponent<CharacterBehaviour>().Say(dialogue, duration);
    }
    
    void ExecuteInitiateInteraction(Character c, JObject props, string sessionId)
    {
        string targetName = props["target_character"].ToString();
        string opening = props["opening"].ToString();
        Character target = FindCharacter(targetName);
        
        float duration = CalculateSpeechDuration(opening);
        c.GetComponent<CharacterBehaviour>().Say(opening, duration);
        c.GetComponent<CharacterBehaviour>().Talk(true);
        
        if (target != null)
        {
            target.GetComponent<CharacterBehaviour>().Talk(true);
            InteractionHandler.Instance.OnInteractionStarted(c, target, sessionId);
        }
        else
        {
            Debug.LogError($"[ACTION ERROR] Failed to find target character '{targetName}' for interaction initiated by {c.name}. Session {sessionId} may be orphaned in database.");
            // Still set up initiator's interaction state so delayed turn triggers work
            // The backend has already created the session, so we need to track it
            if (!string.IsNullOrEmpty(sessionId))
            {
                InteractionHandler.Instance.OnInteractionStartedPartial(c, sessionId);
            }
        }
    }
    
    void ExecuteSpeakInInteraction(Character c, string dialogue, string sessionId)
    {
        float duration = CalculateSpeechDuration(dialogue);
        c.GetComponent<CharacterBehaviour>().Say(dialogue, duration);
        c.GetComponent<CharacterBehaviour>().Talk(true);
    }
    
    /// <summary>
    /// Calculate speech bubble duration based on word count.
    /// Uses 0.2s per word, clamped between 2-9 seconds.
    /// </summary>
    float CalculateSpeechDuration(string text)
    {
        if (string.IsNullOrEmpty(text)) return 2.0f;
        int wordCount = text.Split(new[] { ' ', '\n', '\r' }, System.StringSplitOptions.RemoveEmptyEntries).Length;
        return Mathf.Clamp(wordCount * 0.2f + 0.5f, 2.0f, 9.0f);
    }
    
    void ExecuteFightAction(Character c, string action)
    {
        c.GetComponent<CharacterBehaviour>().Fight(true);
        // Could add specific animations based on action (punch, kick, etc.)
    }
    
    void ExecuteRomanceAction(Character c, string action)
    {
        switch (action.ToLower())
        {
            case "kiss":
                c.GetComponent<CharacterBehaviour>().Kiss(true);
                break;
            case "hug":
            case "hold_hands":
            default:
                c.GetComponent<CharacterBehaviour>().Kiss(true); // Fallback
                break;
        }
    }
    
    void ExecuteLeaveInteraction(Character c, string sessionId)
    {
        c.GetComponent<CharacterBehaviour>().Talk(false);
        InteractionHandler.Instance.OnInteractionEnded(sessionId);
    }
    
    IEnumerator WaitForArrivalThenInteract(Character c, string objectName, string flavor, int generation)
    {
        yield return new WaitUntil(() => !c.GetComponent<CharacterBehaviour>().IsWalking);
        
        // Only proceed if this is still the current generation (not superseded by a newer action)
        if (!movementGeneration.TryGetValue(c, out int current) || current != generation)
        {
            Debug.Log($"[ACTION] Stale use_object coroutine for {c.name} (gen {generation}, current {current}) - skipping");
            yield break;
        }
        
        // Notify backend BEFORE starting interaction
        yield return NotifyActivity(c, "started_using", objectName, $"using {objectName}");
        
        c.GetComponent<CharacterBehaviour>().Interact(true);
        if (!string.IsNullOrEmpty(flavor))
            c.GetComponent<CharacterBehaviour>().Say(flavor, 3);
    }
    
    IEnumerator WaitForArrivalAndNotify(Character c, string destination, int generation)
    {
        yield return new WaitUntil(() => !c.GetComponent<CharacterBehaviour>().IsWalking);
        
        // Only notify if this is still the current generation (not superseded by a newer movement)
        if (movementGeneration.TryGetValue(c, out int current) && current == generation)
        {
            yield return NotifyActivity(c, "arrived", destination, $"arrived at {destination}");
        }
        else
        {
            Debug.Log($"[ACTION] Stale arrival coroutine for {c.name} (gen {generation}, current {current}) - skipping");
        }
    }
    
    IEnumerator NotifyActivity(Character c, string activityType, string target, string description)
    {
        var request = new { activity_type = activityType, target = target, description = description };
        string json = JsonConvert.SerializeObject(request);
        string url = $"http://localhost:8000/characters/{c.characterId}/activity";
        
        using (UnityWebRequest www = UnityWebRequest.Post(url, json, "application/json"))
        {
            yield return www.SendWebRequest();
            // Fire and forget - don't block on response
        }
    }
    
    public Character FindCharacter(string nameOrId)
    {
        if (string.IsNullOrEmpty(nameOrId)) return null;
        
        // Normalize: convert underscores to spaces, and create lowercase ID version
        string withSpaces = nameOrId.Replace("_", " ");
        string asId = nameOrId.ToLower().Replace(" ", "_");
        
        // Try exact GameObject name match first
        GameObject go = GameObject.Find(nameOrId);
        if (go != null)
        {
            Character c = go.GetComponent<Character>();
            if (c != null) return c;
        }
        
        // Try with spaces (e.g., "Sarah_Reeves" → "Sarah Reeves")
        go = GameObject.Find(withSpaces);
        if (go != null)
        {
            Character c = go.GetComponent<Character>();
            if (c != null) return c;
        }
        
        // Try by character ID (case-insensitive)
        Character[] allChars = FindObjectsByType<Character>(FindObjectsSortMode.None);
        return allChars.FirstOrDefault(c => 
            string.Equals(c.characterId, asId, System.StringComparison.OrdinalIgnoreCase) ||
            string.Equals(c.characterId, nameOrId, System.StringComparison.OrdinalIgnoreCase) ||
            string.Equals(c.name, nameOrId, System.StringComparison.OrdinalIgnoreCase) ||
            string.Equals(c.name, withSpaces, System.StringComparison.OrdinalIgnoreCase)
        );
    }
}
