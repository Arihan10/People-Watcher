using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class DecisionManager : MonoBehaviour
{
    public static DecisionManager Instance;
    
    const int MAX_CONCURRENT = 5;
    int activeCount = 0;
    
    Dictionary<Character, CharacterDecisionState> states = new Dictionary<Character, CharacterDecisionState>();
    
    public enum DecisionPriority
    {
        Low = 0,      // Ambient observations ("saw a bird")
        Normal = 1,   // Standard triggers ("entered space", "proximity")
        High = 2,     // Direct actions ("someone spoke to me")
        Critical = 3  // Interrupts ("being attacked")
    }
    
    public class CharacterDecisionState
    {
        public bool isProcessing = false;
        public bool isInInteraction = false;
        public string activeSessionId = null;
        public Queue<PendingDecision> queue = new Queue<PendingDecision>();
        
        // Pending interaction turn - takes precedence over normal queue
        public InteractionTurnInfo pendingInteractionTurn = null;
    }
    
    public class PendingDecision
    {
        public string trigger;
        public DecisionPriority priority;
        public float timestamp;
        
        public PendingDecision(string t, DecisionPriority p)
        {
            trigger = t;
            priority = p;
            timestamp = Time.time;
        }
    }
    
    /// <summary>
    /// Holds information about a pending interaction turn.
    /// </summary>
    public class InteractionTurnInfo
    {
        public string sessionId;
        public string context;
        
        public InteractionTurnInfo(string s, string c)
        {
            sessionId = s;
            context = c;
        }
    }
    
    void Awake()
    {
        if (Instance == null)
            Instance = this;
        else
            Destroy(gameObject);
    }
    
    public void QueueDecision(Character c, string trigger, DecisionPriority priority = DecisionPriority.Normal)
    {
        var state = GetOrCreate(c);
        
        // If in interaction and not critical, ignore
        if (state.isInInteraction && priority < DecisionPriority.Critical)
        {
            // Interaction turns are triggered directly, not queued
            return;
        }
        
        // If already processing, queue it
        if (state.isProcessing)
        {
            state.queue.Enqueue(new PendingDecision(trigger, priority));
            return;
        }
        
        // Check global concurrency limit
        if (activeCount >= MAX_CONCURRENT)
        {
            state.queue.Enqueue(new PendingDecision(trigger, priority));
            return;
        }
        
        // Process now
        StartCoroutine(ProcessDecision(c, trigger, priority));
    }
    
    IEnumerator ProcessDecision(Character c, string trigger, DecisionPriority priority)
    {
        var state = GetOrCreate(c);
        state.isProcessing = true;
        activeCount++;
        
        yield return c.Decide(trigger, (int)priority);
        
        activeCount--;
        state.isProcessing = false;
        
        // If interaction started while this was processing,
        // prioritize pending interaction turn over normal queue
        if (state.isInInteraction)
        {
            // Discard stale normal triggers - they're no longer relevant
            state.queue.Clear();
            
            // Check for pending interaction turn
            if (state.pendingInteractionTurn != null)
            {
                var pending = state.pendingInteractionTurn;
                state.pendingInteractionTurn = null;
                StartCoroutine(ProcessInteractionTurn(c, pending.sessionId, pending.context));
            }
            yield break;
        }
        
        // Process next in queue if any
        if (state.queue.Count > 0)
        {
            var next = state.queue.Dequeue();
            StartCoroutine(ProcessDecision(c, next.trigger, next.priority));
        }
    }
    
    /// <summary>
    /// Queue an interaction turn for processing.
    /// Interaction turns take priority and are serialized per-character.
    /// </summary>
    public void QueueInteractionTurn(Character c, string sessionId, string context)
    {
        var state = GetOrCreate(c);
        
        // Interaction turns supersede any pending normal triggers
        state.queue.Clear();
        
        // If currently processing another decision, store this turn for later
        if (state.isProcessing)
        {
            // Warn if overwriting an existing pending turn (shouldn't normally happen)
            if (state.pendingInteractionTurn != null)
            {
                Debug.LogWarning($"[DECISION] {c.name} - overwriting pending turn for session {Character.ShortSessionId(state.pendingInteractionTurn.sessionId)} with new turn for {Character.ShortSessionId(sessionId)}! This may indicate a bug.");
            }
            
            Debug.Log($"[DECISION] {c.name} is busy, queuing interaction turn for session {Character.ShortSessionId(sessionId)}");
            state.pendingInteractionTurn = new InteractionTurnInfo(sessionId, context);
            return;
        }
        
        // Process immediately
        StartCoroutine(ProcessInteractionTurn(c, sessionId, context));
    }
    
    IEnumerator ProcessInteractionTurn(Character c, string sessionId, string context)
    {
        var state = GetOrCreate(c);
        state.isProcessing = true;
        activeCount++;
        
        Debug.Log($"[DECISION] Processing interaction turn for {c.name} in session {Character.ShortSessionId(sessionId)}");
        
        yield return c.DecideInInteraction(sessionId, context);
        
        activeCount--;
        state.isProcessing = false;
        
        // Check for pending interaction turn (next turn arrived while this was processing)
        if (state.pendingInteractionTurn != null)
        {
            var pending = state.pendingInteractionTurn;
            state.pendingInteractionTurn = null;
            StartCoroutine(ProcessInteractionTurn(c, pending.sessionId, pending.context));
            yield break;
        }
        
        // Note: Don't process normal queue while in interaction
        // Normal triggers are blocked by QueueDecision when isInInteraction is true
    }
    
    public void SetInInteraction(Character c, bool value, string sessionId = null)
    {
        var state = GetOrCreate(c);
        bool wasInInteraction = state.isInInteraction;
        state.isInInteraction = value;
        state.activeSessionId = sessionId;
        
        // Keep Character in sync
        c.SetInteractionState(value, sessionId);
        
        if (value)
        {
            // Clear outdated queue when entering interaction
            state.queue.Clear();
            if (!wasInInteraction)
            {
                Debug.Log($"[DECISION] {c.name} entered interaction, session {Character.ShortSessionId(sessionId)}");
            }
        }
        else if (wasInInteraction)
        {
            Debug.Log($"[DECISION] {c.name} left interaction");
        }
    }
    
    CharacterDecisionState GetOrCreate(Character c)
    {
        if (!states.ContainsKey(c))
        {
            states[c] = new CharacterDecisionState();
        }
        return states[c];
    }
}
