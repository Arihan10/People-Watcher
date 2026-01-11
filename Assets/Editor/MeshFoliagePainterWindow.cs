#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using UnityEditorInternal;

public class MeshFoliagePainterWindow : EditorWindow
{
    [Header("Paint Prefab")]
    public GameObject grassPrefab;
    public Transform parentContainer;

    [Header("Brush")]
    public float brushRadius = 1.5f;
    public int instancesPerStroke = 10;
    public float minSpacing = 0.15f; // prevents clumps
    public bool alignToNormal = true;
    public float normalAlignStrength = 1.0f; // 1 = fully align

    [Header("Randomization")]
    public Vector2 randomScale = new Vector2(0.85f, 1.25f);
    public bool randomYaw = true;
    public Vector2 randomYawDegrees = new Vector2(0f, 360f);

    [Header("Filters")]
    public LayerMask paintLayers = ~0; // default: everything
    public float maxSlopeDegrees = 55f; // 0 = flat only, 90 = any slope

    [Header("Erase")]
    public bool eraseModeHoldShift = true;
    public float eraseRadiusMultiplier = 1.0f;

    [Header("Hotkeys")]
    public bool enablePainting = true;

    private bool _isPainting;

    [MenuItem("Tools/Grass Painter (Mesh)")]
    public static void ShowWindow()
    {
        var w = GetWindow<MeshFoliagePainterWindow>();
        w.titleContent = new GUIContent("Grass Painter");
        w.Show();
    }

    private void OnEnable()
    {
        SceneView.duringSceneGui += OnSceneGUI;
    }

    private void OnDisable()
    {
        SceneView.duringSceneGui -= OnSceneGUI;
    }

    private void OnGUI()
    {
        EditorGUILayout.Space();
        enablePainting = EditorGUILayout.Toggle("Enable Painting", enablePainting);

        EditorGUILayout.Space();
        grassPrefab = (GameObject)EditorGUILayout.ObjectField("Grass Prefab", grassPrefab, typeof(GameObject), false);
        parentContainer = (Transform)EditorGUILayout.ObjectField("Parent Container", parentContainer, typeof(Transform), true);

        EditorGUILayout.Space();
        brushRadius = EditorGUILayout.Slider("Brush Radius", brushRadius, 0.05f, 50f);
        instancesPerStroke = EditorGUILayout.IntSlider("Instances / Stroke", instancesPerStroke, 1, 200);
        minSpacing = EditorGUILayout.Slider("Min Spacing", minSpacing, 0f, 2f);

        EditorGUILayout.Space();
        alignToNormal = EditorGUILayout.Toggle("Align To Normal", alignToNormal);
        normalAlignStrength = EditorGUILayout.Slider("Normal Align Strength", normalAlignStrength, 0f, 1f);

        EditorGUILayout.Space();
        randomScale = EditorGUILayout.Vector2Field("Random Scale (min,max)", randomScale);
        randomYaw = EditorGUILayout.Toggle("Random Yaw", randomYaw);
        randomYawDegrees = EditorGUILayout.Vector2Field("Yaw Range", randomYawDegrees);

        EditorGUILayout.Space();
        paintLayers = LayerMaskField("Paint Layers", paintLayers);
        maxSlopeDegrees = EditorGUILayout.Slider("Max Slope Degrees", maxSlopeDegrees, 0f, 90f);

        EditorGUILayout.Space();
        EditorGUILayout.LabelField("Erase", EditorStyles.boldLabel);
        eraseModeHoldShift = EditorGUILayout.Toggle("Hold Shift to Erase", eraseModeHoldShift);
        eraseRadiusMultiplier = EditorGUILayout.Slider("Erase Radius Multiplier", eraseRadiusMultiplier, 0.25f, 5f);

        EditorGUILayout.Space();
        EditorGUILayout.HelpBox(
            "Usage:\n" +
            "- Left Click + Drag to paint\n" +
            "- Hold Shift while painting to erase (if enabled)\n" +
            "- Make sure the island mesh has a collider (MeshCollider recommended).",
            MessageType.Info
        );

        if (GUILayout.Button("Create Parent Container"))
        {
            var go = new GameObject("Grass_Container");
            Undo.RegisterCreatedObjectUndo(go, "Create Grass Container");
            parentContainer = go.transform;
            Selection.activeGameObject = go;
        }
    }

    private void OnSceneGUI(SceneView view)
    {
        if (!enablePainting) return;

        // Avoid painting while alt/ctrl used for camera controls
        Event e = Event.current;
        if (e == null) return;

        // We want mouse events in scene view
        HandleUtility.AddDefaultControl(GUIUtility.GetControlID(FocusType.Passive));

        Ray ray = HandleUtility.GUIPointToWorldRay(e.mousePosition);

        if (!Physics.Raycast(ray, out RaycastHit hit, 10000f, paintLayers, QueryTriggerInteraction.Ignore))
        {
            return;
        }

        // Draw brush preview
        Handles.color = Color.white;
        Handles.DrawWireDisc(hit.point, hit.normal, brushRadius);

        bool wantsErase = eraseModeHoldShift && e.shift;
        float usedEraseRadius = brushRadius * eraseRadiusMultiplier;

        // Start/stop painting with left mouse
        if (e.type == EventType.MouseDown && e.button == 0 && !e.alt)
        {
            _isPainting = true;
            e.Use();
        }
        if (e.type == EventType.MouseUp && e.button == 0)
        {
            _isPainting = false;
            e.Use();
        }

        if (!_isPainting) return;

        // On drag or repaint, apply paint/erase
        if (e.type == EventType.MouseDrag || e.type == EventType.MouseDown)
        {
            if (wantsErase)
            {
                EraseAt(hit.point, usedEraseRadius);
            }
            else
            {
                PaintAt(hit.point, hit.normal);
            }
            e.Use();
        }
    }

    private void PaintAt(Vector3 center, Vector3 surfaceNormal)
    {
        if (grassPrefab == null) return;

        if (parentContainer == null)
        {
            var go = GameObject.Find("Grass_Container") ?? new GameObject("Grass_Container");
            parentContainer = go.transform;
        }

        // Slope filter
        float slope = Vector3.Angle(surfaceNormal, Vector3.up);
        if (slope > maxSlopeDegrees) return;

        for (int i = 0; i < instancesPerStroke; i++)
        {
            // Random point in brush circle
            Vector2 r = Random.insideUnitCircle * brushRadius;
            Vector3 pos = center + new Vector3(r.x, 2f, r.y);

            // Raycast down from above to find exact mesh point
            if (!Physics.Raycast(pos, Vector3.down, out RaycastHit h, 10f, paintLayers, QueryTriggerInteraction.Ignore))
                continue;

            // Slope filter per point
            float s = Vector3.Angle(h.normal, Vector3.up);
            if (s > maxSlopeDegrees) continue;

            // Spacing check (cheap): reject if too close to existing children
            if (minSpacing > 0f && IsTooClose(h.point, minSpacing))
                continue;

            // Instantiate prefab properly (keeps prefab link)
            GameObject inst = (GameObject)PrefabUtility.InstantiatePrefab(grassPrefab);
            Undo.RegisterCreatedObjectUndo(inst, "Paint Grass");
            inst.transform.SetParent(parentContainer, true);
            inst.transform.position = h.point;

            // Rotation
            Quaternion rot = Quaternion.identity;

            if (alignToNormal)
            {
                Quaternion normalRot = Quaternion.FromToRotation(Vector3.up, h.normal);
                rot = Quaternion.Slerp(Quaternion.identity, normalRot, Mathf.Clamp01(normalAlignStrength));
            }

            if (randomYaw)
            {
                float yaw = Random.Range(randomYawDegrees.x, randomYawDegrees.y);
                rot = Quaternion.Euler(0f, yaw, 0f) * rot;
            }

            inst.transform.rotation = rot;

            // Scale
            float sMin = Mathf.Min(randomScale.x, randomScale.y);
            float sMax = Mathf.Max(randomScale.x, randomScale.y);
            float sc = Random.Range(sMin, sMax);
            inst.transform.localScale = Vector3.one * sc;
        }
    }

    private void EraseAt(Vector3 center, float radius)
    {
        if (parentContainer == null) return;

        // Simple erase: remove children within radius
        // (OK for thousands; for hundreds of thousands you’d want spatial hashing)
        int removed = 0;
        for (int i = parentContainer.childCount - 1; i >= 0; i--)
        {
            Transform child = parentContainer.GetChild(i);
            if ((child.position - center).sqrMagnitude <= radius * radius)
            {
                Undo.DestroyObjectImmediate(child.gameObject);
                removed++;
            }
        }
    }

    private bool IsTooClose(Vector3 p, float spacing)
    {
        if (parentContainer == null) return false;
        float s2 = spacing * spacing;

        // Quick local scan
        int count = parentContainer.childCount;
        // Don’t scan forever if huge; this is a simple tool
        int start = Mathf.Max(0, count - 500); // only check last ~500 for speed
        for (int i = start; i < count; i++)
        {
            Transform t = parentContainer.GetChild(i);
            if ((t.position - p).sqrMagnitude < s2) return true;
        }
        return false;
    }

    // Proper LayerMask field in editor window
    private static LayerMask LayerMaskField(string label, LayerMask selected)
    {
        var layers = InternalEditorUtility.layers;
        int maskWithoutEmpty = 0;

        for (int i = 0; i < layers.Length; i++)
        {
            int layer = LayerMask.NameToLayer(layers[i]);
            if (((1 << layer) & selected.value) != 0)
                maskWithoutEmpty |= (1 << i);
        }

        maskWithoutEmpty = EditorGUILayout.MaskField(label, maskWithoutEmpty, layers);

        int mask = 0;
        for (int i = 0; i < layers.Length; i++)
        {
            if ((maskWithoutEmpty & (1 << i)) != 0)
                mask |= (1 << LayerMask.NameToLayer(layers[i]));
        }

        selected.value = mask;
        return selected;
    }
}
#endif
