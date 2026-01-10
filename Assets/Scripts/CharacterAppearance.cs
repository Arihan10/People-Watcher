using System.Linq;
using UnityEngine;

/// <summary>
/// Manage which top, bottom and shoes are active on the character.
/// Place references to the category GameObjects in the inspector (tops, bottoms, shoes).
/// Call SetTop/SetBottom/SetShoes with an index to activate that item and deactivate the others.
/// </summary>
public class CharacterAppearance : MonoBehaviour
{
    [Header("Category objects - fill these in the Inspector")]
    [SerializeField] private GameObject[] tops = new GameObject[0];
    [SerializeField] private GameObject[] bottoms = new GameObject[0];
    [SerializeField] private GameObject[] shoes = new GameObject[0];
    [SerializeField] private GameObject[] hairs = new GameObject[0];

    [Header("Skin renderers - child SkinnedMeshRenderers (first material will be colored)")]
    [SerializeField] private SkinnedMeshRenderer[] skinRenderers = new SkinnedMeshRenderer[0];

    [Header("Current selection (index)")]
    [SerializeField] private int currentTop = -1;
    [SerializeField] private int currentBottom = -1;
    [SerializeField] private int currentShoes = -1;
    [SerializeField] private int currentHair = -1;
    [Header("Skin color")]
    [SerializeField] private Color currentSkinColor = Color.white;

    private void Start()
    {
        // Ensure the currently selected indices are applied at start (if set in inspector)
        if (tops != null && tops.Length > 0)
        {
            if (currentTop < 0 || currentTop >= tops.Length)
            {
                // find first active top or default to 0
                var firstActive = System.Array.FindIndex(tops, g => g != null && g.activeSelf);
                currentTop = firstActive >= 0 ? firstActive : 0;
            }
            ApplyCategory(tops, currentTop);
        }

        if (bottoms != null && bottoms.Length > 0)
        {
            if (currentBottom < 0 || currentBottom >= bottoms.Length)
            {
                var firstActive = System.Array.FindIndex(bottoms, g => g != null && g.activeSelf);
                currentBottom = firstActive >= 0 ? firstActive : 0;
            }
            ApplyCategory(bottoms, currentBottom);
        }

        if (shoes != null && shoes.Length > 0)
        {
            if (currentShoes < 0 || currentShoes >= shoes.Length)
            {
                var firstActive = System.Array.FindIndex(shoes, g => g != null && g.activeSelf);
                currentShoes = firstActive >= 0 ? firstActive : 0;
            }
            ApplyCategory(shoes, currentShoes);
        }

        if (hairs != null && hairs.Length > 0)
        {
            if (currentHair < 0 || currentHair >= hairs.Length)
            {
                var firstActive = System.Array.FindIndex(hairs, g => g != null && g.activeSelf);
                currentHair = firstActive >= 0 ? firstActive : 0;
            }
            ApplyCategory(hairs, currentHair);
        }

        // Apply skin color to skinned mesh renderers if present
        if (skinRenderers != null && skinRenderers.Length > 0)
        {
            SetSkinColor(currentSkinColor);
        }
    }

    /// <summary>
    /// Activate the top at index and deactivate others.
    /// </summary>
    public void SetTop(int index)
    {
        if (!ValidateAndWarn(tops, index, "Top")) return;
        currentTop = index;
        ApplyCategory(tops, index);
    }

    /// <summary>
    /// Activate the bottom at index and deactivate others.
    /// </summary>
    public void SetBottom(int index)
    {
        if (!ValidateAndWarn(bottoms, index, "Bottom")) return;
        currentBottom = index;
        ApplyCategory(bottoms, index);
    }

    /// <summary>
    /// Activate the shoes at index and deactivate others.
    /// </summary>
    public void SetShoes(int index)
    {
        if (!ValidateAndWarn(shoes, index, "Shoes")) return;
        currentShoes = index;
        ApplyCategory(shoes, index);
    }

    /// <summary>
    /// Activate the hair at index and deactivate others.
    /// </summary>
    public void SetHair(int index)
    {
        if (!ValidateAndWarn(hairs, index, "Hair")) return;
        currentHair = index;
        ApplyCategory(hairs, index);
    }

    /// <summary>
    /// Set the skin color for all configured SkinnedMeshRenderers by changing their first material's color.
    /// </summary>
    public void SetSkinColor(Color color)
    {
        currentSkinColor = color;
        if (skinRenderers == null || skinRenderers.Length == 0)
        {
            Debug.LogWarning($"No skin renderers assigned on '{name}'. Add them in the inspector or use Auto Populate Skinned Renderers.");
            return;
        }

        foreach (var smr in skinRenderers)
        {
            if (smr == null) continue;

            Material mat;
            try
            {
                // Accessing .material gives an instance of the first material for the renderer
                mat = smr.material;
            }
            catch
            {
                continue;
            }

            if (mat == null) continue;

            mat.SetColor("_Color_A_2", color);
        }
    }

    /// <summary>
    /// Sets all three at once.
    /// </summary>
    public void SetAppearance(int topIndex, int bottomIndex, int shoesIndex)
    {
        SetTop(topIndex);
        SetBottom(bottomIndex);
        SetShoes(shoesIndex);
    }

    /// <summary>
    /// Set top, bottom, shoes and hair in one call.
    /// </summary>
    public void SetAppearance(int topIndex, int bottomIndex, int shoesIndex, int hairIndex)
    {
        SetTop(topIndex);
        SetBottom(bottomIndex);
        SetShoes(shoesIndex);
        SetHair(hairIndex);
    }

    private void ApplyCategory(GameObject[] category, int indexToEnable)
    {
        for (int i = 0; i < category.Length; i++)
        {
            var go = category[i];
            if (go == null) continue;
            go.SetActive(i == indexToEnable);
        }
    }

    private bool ValidateAndWarn(GameObject[] category, int index, string displayName)
    {
        if (category == null || category.Length == 0)
        {
            Debug.LogWarning($"{displayName} category is empty on '{name}'. Populate the array in the inspector or use Auto Populate From Children.");
            return false;
        }

        if (index < 0 || index >= category.Length)
        {
            Debug.LogWarning($"{displayName} index {index} is out of range (0..{category.Length - 1}).");
            return false;
        }

        return true;
    }
}
