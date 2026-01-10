// Space.cs
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

public class Space : MonoBehaviour
{
    public string spaceName, spaceDescription;
    Collider col;
    List<GameObject> interactables = new List<GameObject>();
    List<Character> characters = new List<Character>();
    bool playerPresent = false;

    [System.Serializable]
    public class ContextRequest
    {
        public string space_name;
        public string[] characters_present;
        public string[] available_objects;
    }

    [System.Serializable]
    public class ContextResponse
    {
        public string space_name;
        public string description;
    }

    void Start()
    {
        spaceName = name;
        col = GetComponent<Collider>();
        Collider[] overlapping = Physics.OverlapBox(col.bounds.center, col.bounds.extents);

        foreach (Collider c in overlapping)
        {
            if (c != col && c.CompareTag("Interactable"))
            {
                interactables.Add(c.gameObject);
            }
        }
    }

    void OnTriggerEnter(Collider other)
    {
        if (other.CompareTag("Player"))
        {
            playerPresent = true;
        }
    }

    void OnTriggerExit(Collider other)
    {
        if (other.CompareTag("Player"))
        {
            playerPresent = false;
        }
    }

    public void AddCharacter(Character character)
    {
        if (!characters.Contains(character))
        {
            characters.Add(character);
            StartCoroutine(UpdateSpaceContext());
        }
    }

    public void RemoveCharacter(Character character)
    {
        if (characters.Remove(character))
        {
            StartCoroutine(UpdateSpaceContext());
        }
    }

    public string[] GetCharacterNames()
    {
        return characters.Select(c => c.name).ToArray();
    }

    public string[] GetInteractableNames()
    {
        return interactables.Select(i => i.name).ToArray();
    }

    IEnumerator UpdateSpaceContext()
    {
        var request = new ContextRequest
        {
            space_name = spaceName,
            characters_present = GetCharacterNames(),
            available_objects = GetInteractableNames()
        };

        string json = JsonUtility.ToJson(request);

        using (UnityWebRequest www = UnityWebRequest.Post("http://localhost:8000/context/generate-space-context", json, "application/json"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                var response = JsonUtility.FromJson<ContextResponse>(www.downloadHandler.text);
                spaceDescription = response.description;
            }
        }
    }
}