# -*- coding:utf-8 -*-
"""
a test-oriented terminal client for MyGameServer
"""

import select
import socket
import sys
sys.path.append('../')
from server.lobby_exception import IllegalInputException
from server.util import *

RECEIVE_SIZE = 1024
app_buffer = ''


def prompt_prefix():
    """
    print a <You> prefix on screen
    :return: None
    """
    sys.stdout.write('<You> ')
    sys.stdout.flush()


def get_connection(host_IP, port_num):
    """
    client根据服务器IP:port创建客户端的一个连接socket
    :param host_IP:
    :param port_num:
    :return: socket fd for client's connection with server
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
    sock.settimeout(5)
    try:
        is_login = False
        sock.connect((host_IP, port_num))
        sock.send(encode_content("init", code="init"))
        while True:
            global app_buffer
            raw = sock.recv(RECEIVE_SIZE)
            if not raw:
                print 'Exit!\nDisconnected from chat server'
                sys.exit(0)
            app_buffer += raw
            l, new_buffer = decode(app_buffer, 1)
            app_buffer = new_buffer
            l = convert_key(l)
            d = l[0]
            #print(d['content'])
            if d['code'] in ("login_successful", "register_successful"):  # login/reg succeeded
                print("Entering GameLobby...")
                is_login = True
                break
            elif d['code'] == 'exit':
                sock.close()
                print("Client socket is closed")
                sys.exit()
            else:  # 已经打印了response内容, 准备下一个request
                msg_out = sys.stdin.readline().strip()
                msg_out_list = msg_out.split(" ", 1)
                input_code = msg_out_list[0]
                if input_code in ('login', 'l', 'register', 'r'):
                    username_password = msg_out_list[1].split(" ", 1)
                    submit_username = username_password[0].strip()
                    submit_password = username_password[1].strip()
                    submit_code = 'login' if input_code == 'login' else 'register'
                    request = encode({'code': submit_code, 'username': submit_username, 'password': submit_password})
                    sock.send(request)
                elif input_code in ('exit', 'e', 'quit', 'q'):
                    request = encode_content("", code='exit')
                    sock.send(request)
                    sock.close()
                    sys.exit(0)
                else:
                    raise IllegalInputException()
    except IllegalInputException as e:
        print e.message
    except BaseException as e:
        sock.close()
        print 'Unable to connect'
        sys.exit()
    if is_login:
        print 'Connected to remote host. Start sending messages'
        return sock
    else:
        sock.close()
        print 'Unable to connect'
        sys.exit()


def keep_chatting():
    """
    an infinite loop for user's chat
    :return: None
    """
    while True:
        try:
            rlist = [sys.stdin, client_sock]  # input comes from either keyboard or client socket fd

            # Get the list sockets which are readable
            read_list, write_list, error_list = select.select(rlist, [], [])

            for sock in read_list:
                # incoming message from remote server
                if sock == client_sock:
                    raw = sock.recv(RECEIVE_SIZE)
                    # print raw
                    if not raw:
                        print 'Exit!\nDisconnected from chat server'
                        sys.exit(0)
                    else:
                        global app_buffer
                        app_buffer += raw
                        l, new_buffer = decode(raw)
                        app_buffer = new_buffer
                        l = convert_key(l)
                        for d in l:
                            if d['code'] == 'exit':
                                sock.close()
                                print("Client socket is closed")
                                sys.exit(0)
                            else:  # appled for code='msg'
                                sys.stdout.write('\r' + str(d) + '\n')
                                prompt_prefix()

                else:  # user entered a message
                    content = sys.stdin.readline()
                    try:
                        if content.strip() in ('exit', 'e', 'quit', 'q'):
                            client_sock.send(encode({'code': 'exit', 'content': ''}))
                            client_sock.close()
                            print('client exit...')
                            sys.exit(0)
                        else:
                            content_list = content.strip().split(' ')
                            if content_list[0] == 'gds':
                                client_sock.send(encode({'code':'gds', 'score':content_list[1], 'health':content_list[2]}))
                            elif content_list[0] == 'gdr':
                                client_sock.send(encode({'code': 'gdr'}))
                            else:
                                print("input format wrong...")
                        prompt_prefix()
                    except IllegalInputException as e:
                        print(e.message)
        except:
            break


if __name__ == "__main__":
    if len(sys.argv) == 3:
        host = sys.argv[1]
        port = sys.argv[2]
    elif len(sys.argv) == 1:
        host = '127.0.0.1'
        port = 5000
    else:
        print 'Usage : python server.py [hostname] [port]  ([]means optional)'
        sys.exit()
    client_sock = get_connection(host, port)
    prompt_prefix()
    keep_chatting()
