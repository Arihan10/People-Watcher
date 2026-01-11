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
    public float detectionRadius = 6f;
    public float proximityRadius = 3f;
    public string characterId;
    public GameManager.CharacterData characterData;

    List<Space> currentSpaces = new List<Space>();
    CharacterBehaviour characterBehaviour;
    List<Character> nearbyCharacters = new List<Character>();

    [System.Serializable]
    public class DecideRequest
    {
        public string trigger_source;
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
                    GameManager.Instance.UpdateCharacterLocation(this, null);
                else
                    GameManager.Instance.UpdateCharacterLocation(this, currentSpaces[0].spaceName);
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
        AddDecide("Just entered space " + space.spaceName);
    }

    public void AddDecide(string triggerSource)
    {
        if (GameManager.Instance != null)
            GameManager.Instance.QueueDecision(this, triggerSource);
    }

    public IEnumerator Decide(string triggerSource)
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
    /// Coroutine that waits for the character to stop moving, then looks at the object and calls Interact(true).
    /// </summary>
    /// <param name="objectName">The name of the object to look at after reaching destination.</param>
    private IEnumerator WaitForMovementAndInteract(string objectName)
    {
        // Wait until the character is no longer walking or running
        yield return new WaitUntil(() => !characterBehaviour.IsWalking && !characterBehaviour.IsRunning);
        
        // Character has reached destination, look at the object and interact
        characterBehaviour.LookTo(objectName);
        characterBehaviour.Interact(true);
    }


    void ProcessDecisionResponse(string jsonResponse)
    {
        var response = JObject.Parse(jsonResponse);
        var action = response["action"];

        if (action == null) return;

        string actionType = action["actionType"]?.ToString();
        JObject props = action["props"] as JObject;

        switch (actionType)
        {
            case "move":
                characterBehaviour.MoveTo(props["destination"].ToString(), false);
                break;

            case "use_object":
                string objName = props["object_name"].ToString();
                characterBehaviour.MoveTo(objName, false);
                StartCoroutine(WaitForMovementAndInteract(objName));
                break;

            case "speak_in_conversation":
                characterBehaviour.LookTo(props["target_character"].ToString());
                characterBehaviour.Say(props["dialogue"].ToString(), 5);
                break;

            case "fight_in_conversation":
                Debug.Log($"{name} performs {props["action"]} on {props["target_character"]}");
                GameObject.Find(props["target_character"].ToString())?.GetComponent<Character>()?.AddDecide($"{name} started fighting you!");
                characterBehaviour.LookTo(props["target_character"].ToString());
                characterBehaviour.Fight(true);
                break;

            case "romance_in_conversation":
                Debug.Log($"{name} performs {props["action"]} with {props["target_character"]}");
                GameObject.Find(props["target_character"].ToString())?.GetComponent<Character>()?.AddDecide($"{name} is kissing you!");
                characterBehaviour.LookTo(props["target_character"].ToString());
                characterBehaviour.Kiss(true);
                break;

            case "leave_conversation":
                Debug.Log($"{name} leaves conversation with {props["target_character"]}");
                characterBehaviour.Talk(false);
                break;

            case "none":
                Debug.Log($"{name} continues current action");
                break;
        }
    }
}