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
    private Coroutine currentBubbleRoutine;

    // Optional callback when destination is reached
    public event Action OnReachedDestination;

    // Public read-only accessors
    public bool IsWalking => isWalking;
    public bool IsRunning => isRunning;

    // Optional Animator on the same GameObject. If present, we will set its "isWalking" and "isRunning" bool parameters.
    private Animator animator;

    void Awake()
    {
        agent = GetComponent<NavMeshAgent>();
        animator = GetComponent<Animator>();

        // Initialize bubble state
        if (textBubbleRoot != null)
        {
            textBubbleRoot.SetActive(false);
            textBubbleRoot.transform.localScale = Vector3.zero;
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
    /// Sets the Interact animation state. Can loop while true.
    /// If true, automatically stops all other action states (Fight, Talk, Kiss, Sex).
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
    /// Sets the Fight animation state. Can loop while true.
    /// If true, automatically stops all other action states (Interact, Talk, Kiss, Sex).
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
    /// Sets the Kiss animation state. Can loop while true.
    /// If true, automatically stops all other action states (Interact, Fight, Talk, Sex).
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
    /// Sets the Sex animation state. Can loop while true.
    /// If true, automatically stops all other action states (Interact, Fight, Talk, Kiss).
    /// </summary>
    /// <param name="isSexing">True to start/continue sex animation, false to stop and return to idle.</param>
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
        // MoveTo(testObj.transform.position, false);
        Say("HELLO! I am an alien", 3);
    }
}
