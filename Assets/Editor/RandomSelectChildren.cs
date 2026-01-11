#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class RandomSelectChildren
{
    [MenuItem("Tools/Selection/Randomly Select Half of Children")]
    private static void RandomlySelectHalf()
    {
        var active = Selection.activeGameObject;
        if (active == null)
        {
            Debug.LogWarning("Select a parent GameObject first (the one that contains your grass objects).");
            return;
        }

        int n = active.transform.childCount;
        if (n == 0)
        {
            Debug.LogWarning("Selected object has no children.");
            return;
        }

        // Collect children
        var children = new List<GameObject>(n);
        for (int i = 0; i < n; i++)
            children.Add(active.transform.GetChild(i).gameObject);

        // Shuffle
        for (int i = 0; i < children.Count; i++)
        {
            int j = Random.Range(i, children.Count);
            (children[i], children[j]) = (children[j], children[i]);
        }

        // Pick half
        int k = n / 2; // roughly half
        var pick = new GameObject[k];
        for (int i = 0; i < k; i++)
            pick[i] = children[i];

        Selection.objects = pick;
        Debug.Log($"Selected {k} / {n} children from '{active.name}'.");
    }

    [MenuItem("Tools/Selection/Randomly Select Half of Children", true)]
    private static bool Validate()
    {
        return Selection.activeGameObject != null;
    }
}
#endif
