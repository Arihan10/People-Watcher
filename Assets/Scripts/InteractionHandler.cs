using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class InteractionHandler : MonoBehaviour
{
    public static InteractionHandler Instance;
    
    // Track active sessions this client knows about
    Dictionary<string, InteractionSession> activeSessions = new Dictionary<string, InteractionSession>();
    
    public class InteractionSession
    {
        public string sessionId;
        public List<Character> participants;
        public string currentTurn; // character_id
        
        public InteractionSession(string id, List<Character> parts, string turn)
        {
            sessionId = id;
            participants = parts;
            currentTurn = turn;
        }
    }
    
    void Awake()
    {
        if (Instance == null)
            Instance = this;
        else
            Destroy(gameObject);
    }
    
    public void OnInteractionStarted(Character initiator, Character target, string sessionId)
    {
        var session = new InteractionSession(
            sessionId,
            new List<Character> { initiator, target },
            target.characterId
        );
        activeSessions[sessionId] = session;
        
        DecisionManager.Instance.SetInInteraction(initiator, true, sessionId);
        DecisionManager.Instance.SetInInteraction(target, true, sessionId);
        
        // NOTE: Turn triggering is handled by ProcessDecisionResponse via next_turn field,
        // not here. This prevents double-triggering.
    }
    
    /// <summary>
    /// Called when an interaction starts but the target character couldn't be found locally.
    /// Still sets up state for the initiator so delayed turn triggers work correctly.
    /// </summary>
    public void OnInteractionStartedPartial(Character initiator, string sessionId)
    {
        var session = new InteractionSession(
            sessionId,
            new List<Character> { initiator },
            null // Unknown target
        );
        activeSessions[sessionId] = session;
        
        DecisionManager.Instance.SetInInteraction(initiator, true, sessionId);
        
        Debug.Log($"[INTERACTION] Partial start: {initiator.name} in session {Character.ShortSessionId(sessionId)} (target not found locally)");
    }
    
    /// <summary>
    /// Check if a session is known to be active.
    /// </summary>
    public bool IsSessionActive(string sessionId)
    {
        return !string.IsNullOrEmpty(sessionId) && activeSessions.ContainsKey(sessionId);
    }
    
    public void TriggerInteractionTurn(Character c, string sessionId, string context)
    {
        // Route through DecisionManager to ensure single-threaded processing per character
        // This prevents concurrent LLM calls for the same character
        DecisionManager.Instance.QueueInteractionTurn(c, sessionId, context);
    }
    
    public void OnInteractionEnded(string sessionId)
    {
        if (activeSessions.TryGetValue(sessionId, out var session))
        {
            Debug.Log($"[INTERACTION] Session {Character.ShortSessionId(sessionId)} ended with {session.participants.Count} local participants");
            foreach (var c in session.participants)
            {
                if (c != null)
                {
                    DecisionManager.Instance.SetInInteraction(c, false);
                    c.GetComponent<CharacterBehaviour>()?.Talk(false);
                    c.GetComponent<CharacterBehaviour>()?.Fight(false);
                    c.GetComponent<CharacterBehaviour>()?.Kiss(false);
                }
            }
            activeSessions.Remove(sessionId);
        }
        else
        {
            Debug.LogWarning($"[INTERACTION] Tried to end unknown session {Character.ShortSessionId(sessionId)}");
        }
    }
}
