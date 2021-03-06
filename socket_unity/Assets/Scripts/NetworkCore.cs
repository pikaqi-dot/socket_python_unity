using System;
using System.Collections.Generic;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using Tiny;

public class NetworkCore : MonoBehaviour {
	public string serverAddress = "127.0.0.1";
	public int serverPort = 5000;
	public string username = "chen";
	public string password = "123";

	private TcpClient _client;
	private NetworkStream _stream;  // C#中采用NetworkStream的方式, 可以类比于python网络编程中的socket
	private Thread _thread;
	private byte[] _buffer = new byte[1024];  // 接收消息的buffer
	private string receiveMsg = "";
	private bool isConnected = false;


	void Start() {
	}

	public void OnApplicationQuit() {
		Dictionary<string, string> dict = new Dictionary<string, string>()
        {
            {"code", "exit"}
        };
        SendData(Encode(dict));  // 退出的时候先发一个退出的信号给服务器, 使得连接被正确关闭
        Debug.Log("exit sent!");
		CloseConnection ();
	}

    // --------------------public--------------------
	public void Login() {
		SetupConnection();
		Dictionary<string, string> dict = new Dictionary<string, string>()
        {
            {"code", "login"},
            {"username", username},
            {"password", password}
        };
		SendData(Encode(dict));
        Debug.Log("start!");
	}

	public void SendGameData(int score, int health) {
		Dictionary<string, string> dict = new Dictionary<string, string>()
		{
			{"code", "gds"},
			{"score", score.ToString()},
			{"health", health.ToString()}
		};

		SendData(Encode(dict));
	}

    // -----------------------private---------------------
	private void SetupConnection() {
		try {
			_thread = new Thread(ReceiveData);  // 传入函数ReceiveData作为thread的任务
			_thread.IsBackground = true;
			_client = new TcpClient(serverAddress, serverPort);
			_stream = _client.GetStream();
			_thread.Start();  // background thread starts working while loop
			isConnected = true;

		} catch (Exception e) {
			Debug.Log (e.ToString());
			CloseConnection ();
		}
	}

	private void ReceiveData() {  // 这个函数被后台线程执行, 不断地在while循环中跑着
		Debug.Log ("Entered ReceiveData function...");
		if (!isConnected)  // stop the thread
			return;
		int numberOfBytesRead = 0;
		while (isConnected && _stream.CanRead) {
			try {
				numberOfBytesRead = _stream.Read(_buffer, 0, _buffer.Length);
				receiveMsg = Encoding.ASCII.GetString(_buffer, 0, numberOfBytesRead);
				_stream.Flush();
				Debug.Log(receiveMsg);
				receiveMsg = "";
			} catch (Exception e) {
				Debug.Log (e.ToString ());
				CloseConnection ();
			}
		}
	}

	private void SendData(String msgToSend)
    {
        byte[] bytesToSend = Encoding.ASCII.GetBytes(msgToSend);
        if (_stream.CanWrite)
        {
            _stream.Write(bytesToSend, 0, bytesToSend.Length);
        }
    }

	private void CloseConnection() {
		if (isConnected) {
			_thread.Interrupt ();  // 这个其实是多余的, 因为isConnected = false后, 线程while条件为假自动停止
			_stream.Close ();
			_client.Close ();
			isConnected = false;
			receiveMsg = "";
		}
	}

	// ---------------------util----------------------
    // encode dict to to json and wrap it with \r\n as delimiter
	string Encode(Dictionary<string, string> dict)
    {
        string json = Json.Encode(dict);
        string header = "\r\n" + json.Length.ToString() + "\r\n";
		string result = header + json;
		Debug.Log("encode result:" + result);
        return result;

    }
    
	// decode data, 注意要解决粘包的问题, 这个程序写法同GameLobby中的相应模块一模一样
	// 参考 https://github.com/imcheney/GameLobby/blob/master/server/util.py
	Dictionary<string, string> Decode(string raw)
    {
        string payload_str = "";
        string raw_leftover = raw;
        if (raw.Substring(0, 2).Equals("\r\n"))
        {
            int index = raw.IndexOf("\r\n", 2);
            int payload_length = int.Parse(raw.Substring(2, index - 2 + 1));  // 注意, C#'s substring takes start and length as args
            if (raw.Length >= index + 2 + payload_length)
            {
                payload_str = raw.Substring(index + 2, payload_length);
                raw_leftover = raw.Substring(index + 2 + payload_length);
            }
        }
        return Json.Decode<Dictionary<string, string>>(payload_str);
    }

}
