using System.Runtime.Serialization;
using UnityEngine;
using TMPro;

public class UIPanel : MonoBehaviour
{
    
    
    Animator animator;
    [SerializeField] TMP_Text text;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        animator = this.GetComponent<Animator>();

    }

    public void Show(string newText)
    {
        text.text = newText;
        animator.SetBool("Shown", true);
    }

    public void Hide()
    {
        animator.SetBool("Shown", false);
    }
}
