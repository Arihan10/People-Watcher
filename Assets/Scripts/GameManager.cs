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

    Queue<DecisionData> decisionQueue = new Queue<DecisionData>();
    bool isProcessingDecision = false;

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
    }

    public class DecisionData
    {
        public Character character;
        public string triggerSource;

        public DecisionData(Character c, string source)
        {
            character = c;
            triggerSource = source;
        }
    }

    void Awake()
    {
        if (Instance == null)
            Instance = this;
        else
            Destroy(gameObject);

        allSpaces.AddRange(FindObjectsOfType<Space>());
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
                    float x = Random.Range(-10, 10f);
                    float z = Random.Range(-10f, 10f);
                    Vector3 position = new Vector3(x, 2, z);

                    GameObject charObj = Instantiate(characterPrefab, position, Quaternion.identity);
                    charObj.name = data.name;

                    Character character = charObj.GetComponent<Character>();
                    CharacterAppearance characterAppearance = charObj.GetComponent<CharacterAppearance>();
                    characterAppearance.SetAppearance(data.appearance.top, data.appearance.bottom, data.appearance.shoes);
                    character.characterData = data;
                    character.characterId = data.name.ToLower().Replace(" ", "_");
                }
            }
        }
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

    public void QueueDecision(Character character, string triggerSource)
    {
        decisionQueue.Enqueue(new DecisionData(character, triggerSource));

        if (!isProcessingDecision)
            StartCoroutine(ProcessDecisionQueue());
    }

    IEnumerator ProcessDecisionQueue()
    {
        isProcessingDecision = true;

        while (decisionQueue.Count > 0)
        {
            DecisionData decision = decisionQueue.Dequeue();
            yield return StartCoroutine(decision.character.Decide(decision.triggerSource));
        }

        isProcessingDecision = false;
    }
}