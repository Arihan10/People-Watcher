// GameManager.cs
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance;
    public GameObject characterPrefab;

    public List<Space> allSpaces = new List<Space>();
    public Dictionary<Character, string> characterLocations = new Dictionary<Character, string>();

    [System.Serializable]
    public class CharacterLocation
    {
        public string character_name;
        public string space_name;
    }

    [System.Serializable]
    public class GlobalContext
    {
        public string time;
        public string[] all_spaces;
        public CharacterLocation[] character_locations;
    }

    [System.Serializable]
    public class CharacterData
    {
        public int age;
        public AppearanceData appearance;
        public string background;
        public string current_desire;
        public string gender;
        public PositionData position;
        public string name;
        public NeedsData needs;
        public string occupation;
        public string[] personality_traits;
        public string race;
        public string home_space;
    }

    [System.Serializable]
    public class AppearanceData
    {
        public int bottom;
        public int hair;
        public int shoes;
        public int top;
    }

    [System.Serializable]
    public class PositionData
    {
        public float x;
        public float y;
    }

    [System.Serializable]
    public class NeedsData
    {
        public int energy;
        public int happiness;
        public int hunger;
        public int hygiene;
        public int health;
    }

    void Awake()
    {
        if (Instance == null)
            Instance = this;
        else
            Destroy(gameObject);

        allSpaces.AddRange(FindObjectsByType<Space>(FindObjectsSortMode.None));
    }

    void Start()
    {
        StartCoroutine(LoadCharacters());
    }

    IEnumerator LoadCharacters()
    {
        using (UnityWebRequest www = UnityWebRequest.Get("http://localhost:8000/characters"))
        {
            yield return www.SendWebRequest();

            if (www.result == UnityWebRequest.Result.Success)
            {
                var charactersData = JsonConvert.DeserializeObject<CharacterData[]>(www.downloadHandler.text);

                foreach (var data in charactersData)
                {
                    Vector3 position = GetSpawnPosition(data.home_space);

                    GameObject charObj = Instantiate(characterPrefab, position, Quaternion.identity);
                    charObj.name = data.name;

                    Character character = charObj.GetComponent<Character>();
                    CharacterAppearance characterAppearance = charObj.GetComponent<CharacterAppearance>();
                    characterAppearance.SetAppearance(data.appearance.top, data.appearance.bottom, data.appearance.shoes);
                    character.characterData = data;
                    character.characterId = data.name.ToLower().Replace(" ", "_");
                    character.InitializeState();
                }
            }
        }
    }

    Vector3 GetSpawnPosition(string homeSpace)
    {
        // If character has a home space, spawn them there
        if (!string.IsNullOrEmpty(homeSpace))
        {
            // Find the space by name (check both spaceName and GameObject.name)
            Space space = allSpaces.FirstOrDefault(s => 
                s.spaceName == homeSpace || s.gameObject.name == homeSpace);
            
            if (space != null)
            {
                // Get a random position within the space bounds
                Collider col = space.GetComponent<Collider>();
                if (col != null)
                {
                    Vector3 center = col.bounds.center;
                    Vector3 extents = col.bounds.extents * 0.5f; // Stay within inner half
                    
                    float x = center.x + Random.Range(-extents.x, extents.x);
                    float z = center.z + Random.Range(-extents.z, extents.z);
                    
                    return new Vector3(x, 2, z);
                }
            }
        }
        
        // Fallback: random position
        return new Vector3(Random.Range(-10f, 10f), 2, Random.Range(-10f, 10f));
    }

    public void UpdateCharacterLocation(Character character, string spaceName)
    {
        if (spaceName == null)
            characterLocations.Remove(character);
        else
            characterLocations[character] = spaceName;
    }

    public GlobalContext GetGlobalContext()
    {
        var locations = characterLocations
            .Select(kvp => new CharacterLocation
            {
                character_name = kvp.Key.name,
                space_name = kvp.Value
            })
            .ToArray();

        return new GlobalContext
        {
            time = "afternoon",
            all_spaces = allSpaces.Select(s => s.spaceName).ToArray(),
            character_locations = locations
        };
    }

}