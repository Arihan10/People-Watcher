using UnityEngine;
using UnityEditor;
using UnityEngine.Networking;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json;

public class CharacterGeneratorEditor : EditorWindow
{
    private int numCharacters = 10;
    private bool isGenerating = false;
    private string statusMessage = "";
    private List<string> houseSpaces = new List<string>();
    private List<string> allSpaces = new List<string>();

    [System.Serializable]
    public class GenerateRequest
    {
        public int num_characters;
        public string[] house_spaces;
        public string[] all_spaces;
    }

    [System.Serializable]
    public class GenerateResponse
    {
        public string status;
        public string message;
        public int characters_created;
        public int relationships_created;
        public string[] character_names;
    }

    [MenuItem("Village Sim/Generate Characters")]
    public static void ShowWindow()
    {
        var window = GetWindow<CharacterGeneratorEditor>("Character Generator");
        window.RefreshSpaces();
    }

    void OnGUI()
    {
        GUILayout.Label("Village Character Generator", EditorStyles.boldLabel);
        EditorGUILayout.Space();

        numCharacters = EditorGUILayout.IntSlider("Number of Characters", numCharacters, 1, 50);

        EditorGUILayout.Space();
        
        // Show all spaces (for context)
        GUILayout.Label($"All Village Spaces ({allSpaces.Count}):", EditorStyles.boldLabel);
        if (allSpaces.Count > 0)
        {
            EditorGUI.indentLevel++;
            EditorGUILayout.LabelField(string.Join(", ", allSpaces), EditorStyles.wordWrappedLabel);
            EditorGUI.indentLevel--;
        }
        
        EditorGUILayout.Space();
        
        // Show house spaces (for home assignment)
        GUILayout.Label($"House Spaces ({houseSpaces.Count}):", EditorStyles.boldLabel);
        
        if (houseSpaces.Count == 0)
        {
            EditorGUILayout.HelpBox("No house spaces found. Make sure you have Space components with 'House' in the name.", MessageType.Warning);
        }
        else
        {
            EditorGUI.indentLevel++;
            foreach (var space in houseSpaces)
            {
                EditorGUILayout.LabelField("• " + space);
            }
            EditorGUI.indentLevel--;
        }

        EditorGUILayout.Space();

        if (GUILayout.Button("Refresh Spaces"))
        {
            RefreshSpaces();
        }

        EditorGUILayout.Space();

        GUI.enabled = !isGenerating && houseSpaces.Count > 0;
        if (GUILayout.Button(isGenerating ? "Generating..." : "Generate Characters"))
        {
            GenerateCharacters();
        }
        GUI.enabled = true;

        if (!string.IsNullOrEmpty(statusMessage))
        {
            EditorGUILayout.Space();
            EditorGUILayout.HelpBox(statusMessage, isGenerating ? MessageType.Info : 
                (statusMessage.StartsWith("Error") ? MessageType.Error : MessageType.Info));
        }
    }

    void RefreshSpaces()
    {
        houseSpaces.Clear();
        allSpaces.Clear();
        
        // Find all Space components in the scene
        var spaces = FindObjectsByType<Space>(FindObjectsSortMode.None);
        
        foreach (var space in spaces)
        {
            // Get the space name (uses GameObject name if spaceName is empty)
            string spaceName = string.IsNullOrEmpty(space.spaceName) ? space.gameObject.name : space.spaceName;
            
            // Add to all spaces
            allSpaces.Add(spaceName);
            
            // Filter for house-like spaces
            if (spaceName.ToLower().Contains("house") || 
                spaceName.ToLower().Contains("home") ||
                spaceName.ToLower().Contains("cottage") ||
                spaceName.ToLower().Contains("residence"))
            {
                houseSpaces.Add(spaceName);
            }
        }
        
        allSpaces = allSpaces.Distinct().OrderBy(s => s).ToList();
        houseSpaces = houseSpaces.Distinct().OrderBy(s => s).ToList();
        statusMessage = $"Found {allSpaces.Count} total spaces, {houseSpaces.Count} houses.";
        Repaint();
    }

    async void GenerateCharacters()
    {
        isGenerating = true;
        statusMessage = "Connecting to API...";
        Repaint();

        var request = new GenerateRequest
        {
            num_characters = numCharacters,
            house_spaces = houseSpaces.ToArray(),
            all_spaces = allSpaces.ToArray()
        };

        string json = JsonConvert.SerializeObject(request);
        
        try
        {
            using (UnityWebRequest www = UnityWebRequest.Post("http://localhost:8000/generate", json, "application/json"))
            {
                www.timeout = 0; // No timeout - wait indefinitely for LLM response
                
                var operation = www.SendWebRequest();
                
                statusMessage = "Generating characters with AI (this may take 2-3 minutes with extended thinking)...";
                Repaint();
                
                while (!operation.isDone)
                {
                    await System.Threading.Tasks.Task.Delay(100);
                }

                if (www.result == UnityWebRequest.Result.Success)
                {
                    var response = JsonConvert.DeserializeObject<GenerateResponse>(www.downloadHandler.text);
                    
                    if (response.status == "ok")
                    {
                        statusMessage = $"Success! Created {response.characters_created} characters and {response.relationships_created} relationships.\n\nCharacters: {string.Join(", ", response.character_names)}";
                    }
                    else
                    {
                        statusMessage = $"Error: {response.message}";
                    }
                }
                else
                {
                    statusMessage = $"Error: {www.error}\n{www.downloadHandler?.text}";
                }
            }
        }
        catch (System.Exception e)
        {
            statusMessage = $"Error: {e.Message}";
        }

        isGenerating = false;
        Repaint();
    }
}
