using UnityEngine;

public class Billboard : MonoBehaviour
{
    public Transform cameraTransform; // Assign your camera here

    void Start()
    {
        // If cameraTransform is not assigned, find the main camera
        if (cameraTransform == null)
        {
            cameraTransform = Camera.main.transform;
        }
    }

    void Update()
    {
        // Make the canvas look at the camera, but align the up vector with the camera's up vector
        // This keeps the text horizontal relative to the camera's view
        transform.LookAt(transform.position + cameraTransform.rotation * Vector3.forward, cameraTransform.rotation * Vector3.up);
    }
}
