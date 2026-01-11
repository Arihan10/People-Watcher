using System;
using System.Collections; // Required for Coroutines
using UnityEngine;
using UnityEngine.AI;
using TMPro; // Required for TextMeshPro

[RequireComponent(typeof(NavMeshAgent))]
public class CharacterBehaviour : MonoBehaviour
{
    // NavMeshAgent on the same GameObject (required)
    private NavMeshAgent agent;

    // whether the character is currently walking to a destination
    private bool isWalking = false;

    // whether the character is currently running to a destination
    private bool isRunning = false;

    [SerializeField] GameObject testObj;

    [Header("Text Bubble Settings")]
    [SerializeField] private GameObject textBubbleRoot; // Assign the parent object of the bubble
    [SerializeField] private TextMeshProUGUI textBubbleText; // Assign the text component
    [SerializeField] private RectTransform bubblePanelRect; // The panel RectTransform to resize
    [SerializeField] private float baseTopOffset = -50f; // Base top offset for single line
    [SerializeField] private float additionalHeightPerLine = 25f; // Additional height per extra line
    private Coroutine currentBubbleRoutine;
    private float originalTopOffset;

    // Optional callback when destination is reached
    public event Action OnReachedDestination;

    // Public read-only accessors
    public bool IsWalking => isWalking;
    public bool IsRunning => isRunning;

    // Optional Animator on the same GameObject. If present, we will set its "isWalking" and "isRunning" bool parameters.
    private Animator animator;

    // Action coroutine tracking
    private Coroutine currentActionCoroutine;
    private const float ACTION_RANGE = 0.8f;
    private const float DESTINATION_UPDATE_INTERVAL = 0.2f;

    void Awake()
    {
        agent = GetComponent<NavMeshAgent>();
        animator = GetComponent<Animator>();

        // Initialize bubble state
        if (textBubbleRoot != null)
        {
            textBubbleRoot.SetActive(false);
            textBubbleRoot.transform.localScale = Vector3.zero;
            
            // Store original top offset if bubblePanelRect is assigned
            if (bubblePanelRect != null)
            {
                originalTopOffset = -bubblePanelRect.offsetMax.y; // Top in inspector is negative of offsetMax.y
            }
        }
    }

    /// <summary>
    /// Shows a text bubble with a pop-up animation, waits for duration, then pops down.
    /// </summary>
    /// <param name="text">The text to display.</param>
    /// <param name="duration">Time in seconds before disappearing.</param>
    public void Say(string text, float duration = 3f)
    {
        if (textBubbleRoot == null || textBubbleText == null)
        {
            Debug.LogWarning("Text Bubble references missing on CharacterBehaviour!");
            return;
        }

        // Stop any existing bubble animation to reset
        if (currentBubbleRoutine != null) StopCoroutine(currentBubbleRoutine);
        
        currentBubbleRoutine = StartCoroutine(AnimateBubbleRoutine(text, duration));
    }

    private IEnumerator AnimateBubbleRoutine(string text, float duration)
    {
        textBubbleText.text = text;
        textBubbleRoot.SetActive(true);

        // Adjust bubble size based on text line count
        if (bubblePanelRect != null)
        {
            // Force text mesh to update so we can get accurate line count
            textBubbleText.ForceMeshUpdate();
            int lineCount = textBubbleText.textInfo.lineCount;
            
            // Calculate new top offset based on line count
            // More lines = smaller (more negative) top offset = taller bubble
            float extraLines = Mathf.Max(0, lineCount - 1);
            float newTopOffset = baseTopOffset - (extraLines * additionalHeightPerLine);
            
            // Apply the new top offset (top in inspector = -offsetMax.y)
            Vector2 offsetMax = bubblePanelRect.offsetMax;
            offsetMax.y = -newTopOffset;
            bubblePanelRect.offsetMax = offsetMax;
        }

        // Animate In (Scale 0 to 1)
        float timer = 0f;
        float animDuration = 0.25f;
        
        while (timer < animDuration)
        {
            timer += Time.deltaTime;
            float t = timer / animDuration;
            // SmoothStep creates a nice ease-in/ease-out curve
            float scale = Mathf.SmoothStep(0f, 1f, t); 
            textBubbleRoot.transform.localScale = Vector3.one * scale;
            yield return null;
        }
        textBubbleRoot.transform.localScale = Vector3.one;

        // Wait for the reading duration
        yield return new WaitForSeconds(duration);

        // Animate Out (Scale 1 to 0)
        timer = 0f;
        while (timer < animDuration)
        {
            timer += Time.deltaTime;
            float t = timer / animDuration;
            float scale = Mathf.SmoothStep(1f, 0f, t);
            textBubbleRoot.transform.localScale = Vector3.one * scale;
            yield return null;
        }
        
        textBubbleRoot.transform.localScale = Vector3.zero;
        textBubbleRoot.SetActive(false);
    }

    /// <summary>
    /// Finds the nearest GameObject with the given name.
    /// </summary>
    /// <param name="objectName">Name of the object to find.</param>
    /// <returns>The nearest GameObject with that name, or null if not found.</returns>
    private GameObject FindNearestObjectByName(string objectName)
    {
        GameObject[] allObjects = GameObject.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
        GameObject nearestObject = null;
        float nearestDistance = float.MaxValue;

        foreach (GameObject obj in allObjects)
        {
            if (obj.name == objectName)
            {
                float distance = Vector3.Distance(transform.position, obj.transform.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestObject = obj;
                }
            }
        }

        return nearestObject;
    }

    /// <summary>
    /// Rotates the character along the Y axis to face the nearest object with the given name.
    /// </summary>
    /// <param name="objectName">Name of the object(s) to look at. Will look at the nearest one if multiple exist.</param>
    public void LookTo(string objectName)
    {
        // Find all objects with the given name
        GameObject[] allObjects = GameObject.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
        GameObject nearestObject = null;
        float nearestDistance = float.MaxValue;

        foreach (GameObject obj in allObjects)
        {
            if (obj.name == objectName)
            {
                float distance = Vector3.Distance(transform.position, obj.transform.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestObject = obj;
                }
            }
        }

        if (nearestObject == null)
        {
            Debug.LogWarning($"No object with name '{objectName}' found in scene.");
            return;
        }

        // Calculate direction to target on the XZ plane (ignoring Y)
        Vector3 direction = nearestObject.transform.position - transform.position;
        direction.y = 0f;

        if (direction.sqrMagnitude > 0.001f)
        {
            Quaternion targetRotation = Quaternion.LookRotation(direction);
            transform.rotation = targetRotation;
        }
    }

    /// <summary>
    /// Move the character to the nearest object with the given name using the NavMeshAgent on this GameObject.
    /// </summary>
    /// <param name="objectName">Name of the object(s) to move to. Will move to the nearest one if multiple exist.</param>
    /// <param name="run">If true, the character runs (speed 3, isRunning=true). Otherwise walks (speed 1.8, isWalking=true).</param>
    public void MoveTo(string objectName, bool run = false)
    {
        if (agent == null)
        {
            agent = GetComponent<NavMeshAgent>();
            if (agent == null)
            {
                Debug.LogError("CharacterBehaviour requires a NavMeshAgent component.");
                return;
            }
        }

        // Find all objects with the given name
        GameObject[] allObjects = GameObject.FindObjectsByType<GameObject>(FindObjectsSortMode.None);
        GameObject nearestObject = null;
        float nearestDistance = float.MaxValue;

        foreach (GameObject obj in allObjects)
        {
            if (obj.name == objectName)
            {
                float distance = Vector3.Distance(transform.position, obj.transform.position);
                if (distance < nearestDistance)
                {
                    nearestDistance = distance;
                    nearestObject = obj;
                }
            }
        }

        if (nearestObject == null)
        {
            Debug.LogWarning($"No object with name '{objectName}' found in scene.");
            return;
        }

        Vector3 target = nearestObject.transform.position;
        agent.SetDestination(target);

        // Set movement state and speed based on run parameter
        if (run)
        {
            isRunning = true;
            isWalking = false;
            agent.speed = 3f;
            animator?.SetBool("isRunning", true);
            animator?.SetBool("isWalking", false);
        }
        else
        {
            isWalking = true;
            isRunning = false;
            agent.speed = 1.8f;
            animator?.SetBool("isWalking", true);
            animator?.SetBool("isRunning", false);
        }
    }

    /// <summary>
    /// Stops the agent immediately.
    /// </summary>
    public void Stop()
    {
        if (agent != null)
        {
            agent.ResetPath();
        }

        isWalking = false;
        isRunning = false;
        animator?.SetBool("isWalking", false);
        animator?.SetBool("isRunning", false);
    }

    void Update()
    {
        // Simple arrival detection: when a path is not pending and remainingDistance <= stoppingDistance
        if ((isWalking || isRunning) && agent != null && !agent.pathPending)
        {
            if (agent.remainingDistance <= agent.stoppingDistance)
            {
                // when agent has no path or has effectively stopped moving
                if (!agent.hasPath || agent.velocity.sqrMagnitude == 0f)
                {
                    isWalking = false;
                    isRunning = false;
                    animator?.SetBool("isWalking", false);
                    animator?.SetBool("isRunning", false);
                    OnReachedDestination?.Invoke();
                }
            }
        }
    }

    /// <summary>
    /// Stops the current action coroutine and resets all action animation states.
    /// </summary>
    private void StopCurrentAction()
    {
        if (currentActionCoroutine != null)
        {
            StopCoroutine(currentActionCoroutine);
            currentActionCoroutine = null;
        }
        
        // Stop movement
        if (agent != null)
        {
            agent.ResetPath();
        }
        isWalking = false;
        isRunning = false;
        
        // Reset all action animations
        animator?.SetBool("isWalking", false);
        animator?.SetBool("isRunning", false);
        animator?.SetBool("isInteracting", false);
        animator?.SetBool("isFighting", false);
        animator?.SetBool("isTalking", false);
        animator?.SetBool("isKissing", false);
        animator?.SetBool("isSexing", false);
    }

    /// <summary>
    /// Coroutine that moves towards a target object, updating destination periodically for moving targets.
    /// When within range, triggers the specified animation.
    /// </summary>
    private IEnumerator MoveToTargetAndTriggerAction(string targetObjectName, string animationBoolName)
    {
        GameObject targetObject = FindNearestObjectByName(targetObjectName);
        
        if (targetObject == null)
        {
            Debug.LogWarning($"No object with name '{targetObjectName}' found in scene.");
            yield break;
        }

        // FIRST: Clear ALL action animations before anything else
        animator?.SetBool("isInteracting", false);
        animator?.SetBool("isFighting", false);
        animator?.SetBool("isTalking", false);
        animator?.SetBool("isKissing", false);
        animator?.SetBool("isSexing", false);

        // Start walking towards target - walking has highest priority during movement
        isWalking = true;
        isRunning = false;
        agent.speed = 1.8f;
        animator?.SetBool("isWalking", true);
        animator?.SetBool("isRunning", false);
        agent.SetDestination(targetObject.transform.position);

        float timeSinceLastUpdate = 0f;
        bool hasReachedTarget = false;

        while (!hasReachedTarget)
        {
            // Re-find the target in case it's a moving object (like another character)
            targetObject = FindNearestObjectByName(targetObjectName);
            
            if (targetObject == null)
            {
                Debug.LogWarning($"Target '{targetObjectName}' lost during approach.");
                StopCurrentAction();
                yield break;
            }

            float distanceToTarget = Vector3.Distance(transform.position, targetObject.transform.position);

            // Check if we're within action range
            if (distanceToTarget <= ACTION_RANGE)
            {
                hasReachedTarget = true;
                break;
            }

            // Ensure walking animation stays on during movement (highest priority)
            if (isWalking && animator != null)
            {
                animator.SetBool("isWalking", true);
                // Make sure no action animations interfere
                animator.SetBool("isInteracting", false);
                animator.SetBool("isFighting", false);
                animator.SetBool("isTalking", false);
                animator.SetBool("isKissing", false);
                animator.SetBool("isSexing", false);
            }

            // Update destination periodically to handle moving targets
            timeSinceLastUpdate += Time.deltaTime;
            if (timeSinceLastUpdate >= DESTINATION_UPDATE_INTERVAL)
            {
                agent.SetDestination(targetObject.transform.position);
                timeSinceLastUpdate = 0f;
            }

            yield return null;
        }

        // Stop walking
        agent.ResetPath();
        isWalking = false;
        animator?.SetBool("isWalking", false);

        // Face the target
        LookTo(targetObjectName);

        // Clear other action animations and trigger the specified one
        animator?.SetBool("isInteracting", false);
        animator?.SetBool("isFighting", false);
        animator?.SetBool("isTalking", false);
        animator?.SetBool("isKissing", false);
        animator?.SetBool("isSexing", false);
        animator?.SetBool(animationBoolName, true);

        // Keep facing the target while action is active (for moving targets)
        while (true)
        {
            targetObject = FindNearestObjectByName(targetObjectName);
            if (targetObject != null)
            {
                float distanceToTarget = Vector3.Distance(transform.position, targetObject.transform.position);
                
                // If target moves away, follow them
                if (distanceToTarget > ACTION_RANGE * 2f)
                {
                    // Target moved too far, restart approaching
                    // FIRST: Stop action animation
                    animator?.SetBool(animationBoolName, false);
                    
                    // Clear ALL action animations before walking
                    animator?.SetBool("isInteracting", false);
                    animator?.SetBool("isFighting", false);
                    animator?.SetBool("isTalking", false);
                    animator?.SetBool("isKissing", false);
                    animator?.SetBool("isSexing", false);
                    
                    // NOW start walking - walking has highest priority
                    isWalking = true;
                    animator?.SetBool("isWalking", true);
                    agent.SetDestination(targetObject.transform.position);
                    
                    // Wait until we're close again
                    while (distanceToTarget > ACTION_RANGE)
                    {
                        targetObject = FindNearestObjectByName(targetObjectName);
                        if (targetObject == null) yield break;
                        
                        distanceToTarget = Vector3.Distance(transform.position, targetObject.transform.position);
                        agent.SetDestination(targetObject.transform.position);
                        
                        // Keep enforcing walking animation during movement
                        animator?.SetBool("isWalking", true);
                        animator?.SetBool("isInteracting", false);
                        animator?.SetBool("isFighting", false);
                        animator?.SetBool("isTalking", false);
                        animator?.SetBool("isKissing", false);
                        animator?.SetBool("isSexing", false);
                        
                        yield return null;
                    }
                    
                    // Back in range, stop walking FIRST
                    agent.ResetPath();
                    isWalking = false;
                    animator?.SetBool("isWalking", false);
                    
                    // Then face target and resume action
                    LookTo(targetObjectName);
                    animator?.SetBool(animationBoolName, true);
                }
                else
                {
                    // Keep facing the target
                    LookTo(targetObjectName);
                }
            }
            yield return new WaitForSeconds(0.1f);
        }
    }

    /// <summary>
    /// Moves towards the target object and starts the Interact animation when in range.
    /// If isInteracting is false, stops the current action.
    /// </summary>
    /// <param name="targetObjectName">Name of the object to interact with.</param>
    /// <param name="isInteracting">True to start interacting, false to stop.</param>
    public void Interact(string targetObjectName, bool isInteracting)
    {
        StopCurrentAction();
        
        if (isInteracting && !string.IsNullOrEmpty(targetObjectName))
        {
            currentActionCoroutine = StartCoroutine(MoveToTargetAndTriggerAction(targetObjectName, "isInteracting"));
        }
    }

    /// <summary>
    /// Sets the Interact animation state immediately without movement.
    /// If true, automatically stops all other action states.
    /// </summary>
    /// <param name="isInteracting">True to start/continue interacting, false to stop and return to idle.</param>
    public void Interact(bool isInteracting)
    {
        if (isInteracting)
        {
            animator?.SetBool("isFighting", false);
            animator?.SetBool("isTalking", false);
            animator?.SetBool("isKissing", false);
            animator?.SetBool("isSexing", false);
        }
        animator?.SetBool("isInteracting", isInteracting);
    }

    /// <summary>
    /// Moves towards the target object and starts the Fight animation when in range.
    /// If isFighting is false, stops the current action.
    /// </summary>
    /// <param name="targetObjectName">Name of the object/character to fight.</param>
    /// <param name="isFighting">True to start fighting, false to stop.</param>
    public void Fight(string targetObjectName, bool isFighting)
    {
        StopCurrentAction();
        
        if (isFighting && !string.IsNullOrEmpty(targetObjectName))
        {
            currentActionCoroutine = StartCoroutine(MoveToTargetAndTriggerAction(targetObjectName, "isFighting"));
        }
    }

    /// <summary>
    /// Sets the Fight animation state immediately without movement.
    /// If true, automatically stops all other action states.
    /// </summary>
    /// <param name="isFighting">True to start/continue fighting, false to stop and return to idle.</param>
    public void Fight(bool isFighting)
    {
        if (isFighting)
        {
            animator?.SetBool("isInteracting", false);
            animator?.SetBool("isTalking", false);
            animator?.SetBool("isKissing", false);
            animator?.SetBool("isSexing", false);
        }
        animator?.SetBool("isFighting", isFighting);
    }

    /// <summary>
    /// Sets the Talk animation state. Can loop while true.
    /// If true, automatically stops all other action states (Interact, Fight, Kiss, Sex).
    /// </summary>
    /// <param name="isTalking">True to start/continue talking, false to stop and return to idle.</param>
    public void Talk(bool isTalking)
    {
        if (isTalking)
        {
            animator?.SetBool("isInteracting", false);
            animator?.SetBool("isFighting", false);
            animator?.SetBool("isKissing", false);
            animator?.SetBool("isSexing", false);
        }
        animator?.SetBool("isTalking", isTalking);
    }

    /// <summary>
    /// Moves towards the target object and starts the Kiss animation when in range.
    /// If isKissing is false, stops the current action.
    /// </summary>
    /// <param name="targetObjectName">Name of the object/character to kiss.</param>
    /// <param name="isKissing">True to start kissing, false to stop.</param>
    public void Kiss(string targetObjectName, bool isKissing)
    {
        StopCurrentAction();
        
        if (isKissing && !string.IsNullOrEmpty(targetObjectName))
        {
            currentActionCoroutine = StartCoroutine(MoveToTargetAndTriggerAction(targetObjectName, "isKissing"));
        }
    }

    /// <summary>
    /// Sets the Kiss animation state immediately without movement.
    /// If true, automatically stops all other action states.
    /// </summary>
    /// <param name="isKissing">True to start/continue kissing, false to stop and return to idle.</param>
    public void Kiss(bool isKissing)
    {
        if (isKissing)
        {
            animator?.SetBool("isInteracting", false);
            animator?.SetBool("isFighting", false);
            animator?.SetBool("isTalking", false);
            animator?.SetBool("isSexing", false);
        }
        animator?.SetBool("isKissing", isKissing);
    }

    /// <summary>
    /// Moves towards the target object and starts the Sex animation when in range.
    /// If isSexing is false, stops the current action.
    /// </summary>
    /// <param name="targetObjectName">Name of the object/character for the action.</param>
    /// <param name="isSexing">True to start, false to stop.</param>
    public void Sex(string targetObjectName, bool isSexing)
    {
        StopCurrentAction();
        
        if (isSexing && !string.IsNullOrEmpty(targetObjectName))
        {
            currentActionCoroutine = StartCoroutine(MoveToTargetAndTriggerAction(targetObjectName, "isSexing"));
        }
    }

    /// <summary>
    /// Sets the Sex animation state immediately without movement.
    /// If true, automatically stops all other action states.
    /// </summary>
    /// <param name="isSexing">True to start/continue, false to stop and return to idle.</param>
    public void Sex(bool isSexing)
    {
        if (isSexing)
        {
            animator?.SetBool("isInteracting", false);
            animator?.SetBool("isFighting", false);
            animator?.SetBool("isTalking", false);
            animator?.SetBool("isKissing", false);
        }
        animator?.SetBool("isSexing", isSexing);
    }

    void Start() {
        
        Say("I am an alien. HELLO! I am an alien. HELLO! I am an alien. HELLO! I am an alien. HELLO! I am an alien. HELLO! I am an alien. ", 3);
        Kiss(testObj.name, true);
        
    }
}
