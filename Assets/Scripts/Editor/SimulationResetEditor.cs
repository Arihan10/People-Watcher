using UnityEngine;
using UnityEditor;
using UnityEngine.Networking;
using Newtonsoft.Json;

public class SimulationResetEditor : EditorWindow
{
    private bool isResetting = false;
    private string statusMessage = "";

    [System.Serializable]
    public class ResetResponse
    {
        public string status;
        public string message;
        public int characters_reset;
        public int relationships_reset;
    }

    [MenuItem("Village Sim/Reset Simulation")]
    public static void ShowWindow()
    {
        GetWindow<SimulationResetEditor>("Reset Simulation");
    }

    void OnGUI()
    {
        GUILayout.Label("Reset Village Simulation", EditorStyles.boldLabel);
        EditorGUILayout.Space();

        EditorGUILayout.HelpBox(
            "This will reset all characters and relationships to their initial state:\n\n" +
            "• Clear all action and memory logs\n" +
            "• Reset needs and feelings to defaults\n" +
            "• Clear all interaction history\n" +
            "• Clear current activities and positions\n\n" +
            "Character profiles and relationship backgrounds are preserved.",
            MessageType.Info
        );

        EditorGUILayout.Space();

        GUI.enabled = !isResetting;
        
        // Use red color for the reset button to indicate it's a destructive action
        var originalColor = GUI.backgroundColor;
        GUI.backgroundColor = new Color(1f, 0.5f, 0.5f);
        
        if (GUILayout.Button(isResetting ? "Resetting..." : "Reset Simulation", GUILayout.Height(30)))
        {
            if (EditorUtility.DisplayDialog(
                "Reset Simulation",
                "Are you sure you want to reset the simulation?\n\nThis will clear all character history, interactions, and progress.",
                "Reset",
                "Cancel"))
            {
                ResetSimulation();
            }
        }
        
        GUI.backgroundColor = originalColor;
        GUI.enabled = true;

        if (!string.IsNullOrEmpty(statusMessage))
        {
            EditorGUILayout.Space();
            EditorGUILayout.HelpBox(statusMessage, isResetting ? MessageType.Info : 
                (statusMessage.StartsWith("Error") ? MessageType.Error : MessageType.Info));
        }
    }

    async void ResetSimulation()
    {
        isResetting = true;
        statusMessage = "Connecting to API...";
        Repaint();

        try
        {
            using (UnityWebRequest www = UnityWebRequest.Post("http://localhost:8000/reset", "", "application/json"))
            {
                www.timeout = 30;
                
                var operation = www.SendWebRequest();
                
                statusMessage = "Resetting simulation...";
                Repaint();
                
                while (!operation.isDone)
                {
                    await System.Threading.Tasks.Task.Delay(100);
                }

                if (www.result == UnityWebRequest.Result.Success)
                {
                    var response = JsonConvert.DeserializeObject<ResetResponse>(www.downloadHandler.text);
                    
                    if (response.status == "ok")
                    {
                        statusMessage = $"Success! Reset {response.characters_reset} characters and {response.relationships_reset} relationships to initial state.";
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

        isResetting = false;
        Repaint();
    }
}
