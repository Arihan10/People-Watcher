using UnityEngine;
using UnityEngine.InputSystem;

public class CameraMovement : MonoBehaviour
{
    [Header("Movement Settings")]
    public float panSpeed = 0.001f; // Sensitivity for mouse drag

    [Header("Camera Angle")]
    public float pitchAngle = 60f; // Angle looking down (90 is straight down)

    [Header("Height Settings")]
    public float fixedHeight = 40f; // The fixed Y position
    public float zoomedHeight = 7f; // Height when following a character

    [Header("Position Limits")]
    public Vector2 xLimit = new Vector2(-50f, 50f); // Min X, Max X
    public Vector2 zLimit = new Vector2(-50f, 50f); // Min Z, Max Z

    [Header("Follow Settings")]
    public LayerMask characterLayer;
    public Vector3 followOffset = new Vector3(0, 0, -4f); // Offset from character when following
    public float smoothSpeed = 5f;

    private Transform targetToFollow;
    private bool isFollowing = false;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        // Set the initial rotation
        transform.rotation = Quaternion.Euler(pitchAngle, 0f, 0f);
        
        // Set initial height
        Vector3 startPos = transform.position;
        startPos.y = fixedHeight;
        transform.position = startPos;
    }

    // Update is called once per frame
    void Update()
    {
        // Ensure mouse is connected
        if (Mouse.current == null) return;

        // Check for click to select character
        if (Mouse.current.leftButton.wasPressedThisFrame)
        {
            if (Camera.main == null)
            {
                Debug.LogError("Main Camera is missing! Ensure your camera is tagged 'MainCamera'.");
                return;
            }

            Ray ray = Camera.main.ScreenPointToRay(Mouse.current.position.ReadValue());
            
            // Debug: Draw the ray in the Scene view for 2 seconds
            Debug.DrawRay(ray.origin, ray.direction * 1000f, Color.red, 2f);

            if (Physics.Raycast(ray, out RaycastHit hit, 1000f, characterLayer))
            {
                Debug.Log($"Successfully hit character: {hit.transform.name}");
                targetToFollow = hit.transform;
                isFollowing = true;
            }
            else
            {
                // Debug: Find out what we ARE hitting
                if (Physics.Raycast(ray, out RaycastHit debugHit, 1000f))
                {
                    Debug.Log($"Raycast missed 'Character' layer. Instead hit: '{debugHit.transform.name}' on Layer: '{LayerMask.LayerToName(debugHit.transform.gameObject.layer)}'");
                }
                else
                {
                    Debug.Log("Raycast hit nothing at all.");
                }

                isFollowing = false;
                targetToFollow = null;
            }
        }

        if (isFollowing && targetToFollow != null)
        {
            // Calculate target position based on character position + offset
            // We override the Y to be the zoomedHeight
            Vector3 desiredPosition = targetToFollow.position + followOffset;
            desiredPosition.y = zoomedHeight;

            // Smoothly move there
            transform.position = Vector3.Lerp(transform.position, desiredPosition, smoothSpeed * Time.deltaTime);
        }
        else
        {
            HandleFreeMovement();
        }
    }

    void HandleFreeMovement()
    {
        Vector3 pos = transform.position;

        // Mouse Drag Panning (Left Click)
        if (Mouse.current.leftButton.isPressed)
        {
            Vector2 delta = Mouse.current.delta.ReadValue();

            // Move camera opposite to mouse movement to create "drag world" effect
            // We do not multiply by Time.deltaTime because 'delta' is already the pixels moved since the last frame
            pos.x -= delta.x * panSpeed / 300f;
            pos.z -= delta.y * panSpeed / 300f;
        }

        // Clamp positions
        pos.x = Mathf.Clamp(pos.x, xLimit.x, xLimit.y);
        pos.z = Mathf.Clamp(pos.z, zLimit.x, zLimit.y);
        
        // Return to fixed height smoothly if we were zoomed in
        pos.y = Mathf.Lerp(pos.y, fixedHeight, smoothSpeed * Time.deltaTime);

        transform.position = pos;
    }
}
