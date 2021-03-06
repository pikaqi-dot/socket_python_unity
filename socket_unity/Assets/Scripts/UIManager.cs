using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;  //using 关键字用于在程序中包含命名空间。一个程序可以包含多个 using 语句。

public class UIManager : MonoBehaviour {
	public InputField scoreInputField;
	public InputField healthInputField;

	NetworkCore networkCore;
	// Use this for initialization
	void Start () {
		networkCore = GetComponent<NetworkCore>();
	}
	
	// Update is called once per frame
	void Update () {
		
	}

	public void OnLoginButton() {
		networkCore.Login();
	}

	public void OnSendButton() {
		int score = int.Parse(scoreInputField.text);
		int health = int.Parse(healthInputField.text);
		networkCore.SendGameData(score, health);
	}

	public void OnQuitButton()
    {
		int score = int.Parse(scoreInputField.text);
        int health = int.Parse(healthInputField.text);
        networkCore.SendGameData(score, health);
		Application.Quit();
    }
}
