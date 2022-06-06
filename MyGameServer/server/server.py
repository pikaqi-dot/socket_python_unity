# -*- coding:utf-8 -*-
"""
MyGameServer, for Unity game's python server part
data store: shelve
"""
from util import *
import select
import shelve
import socket
import sys
import platform
import time
import datetime
import random
import threading
from lobby_exception import ExitException, IllegalInputException


class LobbyServer(object):
    def __init__(self, port=5000):
        self.sys = platform.system()
        if self.sys == 'Windows':  # Windows下不支持select追踪sys.stdin
            self.conn_list = []
        else:
            self.conn_list = [sys.stdin]  # List to keep track of all connected socket descriptors
        self.login_client_list = []  # List to keep track of login user client sock
        self.RECEIVE_SIZE = 1024  # Advisable to keep it as an exponent of 2
        self.app_buffer = ''  # buffer for application level, very important
        self.port = port

        self.SYS_FAKE_SOCK = 0
        self.clientsock_username = {0: 'system'}  # sock -> username mapping, vital for messaging service
        self.users = shelve.open('users', writeback=True)
        for username in self.users.keys():  # 清除所有用户的在线状态, 否则会出现服务器异常退出后, 有些用户仍然为状态在线
             self.users[username]['login_timestamp'] = -1
        # self.rooms = shelve.open('rooms', writeback=True)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(("127.0.0.1", self.port))
        self.server_socket.listen(10)
        self.conn_list.append(self.server_socket)  # server_socket提供新连接事件
        print("Chat server started on port " + str(self.port))

    def loop(self):
        while True:
            try:
                # Get the list sockets which are ready to be read through select
                read_sockets, write_sockets, error_sockets = select.select(self.conn_list, [], [])

                for sock in read_sockets:
                    if sock == self.server_socket:  # New connection
                        new_sock, new_addr = self.server_socket.accept()
                        self.conn_list.append(new_sock)  # 先加入conn_list, 之后根据验证情况决定是否加入到client_list中
                        print("Client sock (%s:%s) connected" % new_addr)
                    elif self.sys != 'Windows' and sock == sys.stdin:  # Windows下禁用这部分逻辑
                        in_content = sys.stdin.readline()
                        if in_content.strip() in ('exit', 'quit'):
                            self.server_exit()
                        else:  # send it to client as test message
                            self.broadcast_content(self.SYS_FAKE_SOCK, self.login_client_list,
                                                   in_content)
                    else:  # Data received from client, process it
                        data = sock.recv(self.RECEIVE_SIZE)
                        #print(data)
                        if not data:
                            raise ExitException('No data, which indicates that this sock should be closed.')
                        else:
                            self.app_buffer += data  # append the new data to the end of app_buffer
                            l, new_buffer = decode(self.app_buffer)
                            self.app_buffer = new_buffer
                            l = convert_key(l)
                            for d in l:
                                code = d['code']
                                print(d)
                                if code == 'exit' or code == 'quit':
                                    raise ExitException("Client demands exit")  # ExitException专门处理需要退出情形
                                elif code in ("init", "i"):
                                    response = encode({'code': "msg", 'content': """menu Welcome to MyGameServer!\n
                                                                              =========command list========
                                                                              1. register username password
                                                                              2. login username password
                                                                              3. exit
                                                                              """})
                                    print('response: ' + response)
                                    sock.send(response)
                                elif code in ("register", "r"):
                                    self.do_register(sock, d)
                                elif code in ("login", "l"):
                                    self.do_login(sock, d)
                                elif code in ('game_data_storage', 'gds'):
                                    self.do_game_data_storage(sock, d)
                                elif code in ('game_data_request', 'gdr'):
                                    self.do_game_data_request(sock)

            except ExitException as e:
                self.tackle_client_exit(sock, e.message)
                continue
            except IllegalInputException as e:
                print(e.message)
                response = encode({'code': "msg", 'content': e.message})
                sock.send(response)
            except KeyboardInterrupt:
                self.server_exit()
            except BaseException as e:
                print(e)  # sys.exit()也会走到这个Exception里面
                break

    # login, register, chat
    def do_login(self, sock, data_dict):
        print("into do_login function...")
        if not data_dict.__contains__('username') or not data_dict.__contains__('password'):
            raise IllegalInputException()
        login_username = data_dict['username']
        login_password = data_dict['password']
        if not self.users.__contains__(login_username):
            response = encode_content("fail Username not found")
            sock.send(response)
        elif self.users[login_username]['password'] != login_password:
            response = encode_content(
                "fail Wrong password for this username")
            sock.send(response)
        elif self.users[login_username]['login_timestamp'] != -1:
            response = encode_content(
                "fail This account is already online")
            sock.send(response)
        else:  # successful
            response = encode({'code':'login_successful', 'score':self.users[login_username]['score'], 'health':self.users[login_username]['health']})
            print("login_successful")
            sock.send(response)
            self.users[login_username]['login_timestamp'] = int(
                time.time())  # update login_timestamp
            self.login_client_list.append(sock)
            self.clientsock_username[sock] = login_username

    def do_register(self, sock, data_dict):
        if not data_dict.__contains__('username') or not data_dict.__contains__('password'):
            raise IllegalInputException()
        reg_username = data_dict['username']
        reg_password = data_dict['password']
        if self.users.__contains__(reg_username):
            response = encode_content("fail Username used, please change your username!")
            sock.send(response)
        else:  # okay
            self.users[reg_username] = {}  # 这里得先创建一个dict, 才能赋值
            self.users[reg_username]['password'] = reg_password
            self.users[reg_username]['reg_timestamp'] = int(time.time())
            # self.users[reg_username]['total_time'] = 0  # init total_time
            self.users[reg_username]['login_timestamp'] = int(time.time())  # the most recent login_time
            self.users[reg_username]['score'] = 0
            self.users[reg_username]['health'] = 100
            # self.users[reg_username]['room'] = '-1'
            response = encode_content(
                "register_successful Succeeded! Your username is {0}, password is {1}".format(
                    reg_username, reg_password), "register_successful")
            sock.send(response)
            self.login_client_list.append(sock)
            self.clientsock_username[sock] = reg_username  # sock --> username
            self.users.sync()

    def do_game_data_storage(self, sock, data_dict):
        if sock not in self.login_client_list:
            response = encode_content("You have not login yet!")
            sock.send(response)
        else:
            username = self.clientsock_username[sock]
            self.users[username]['score'] = int(data_dict['score'])
            self.users[username]['health'] = int(data_dict['health'])

    def do_game_data_request(self, sock):
        username = self.clientsock_username[sock]
        score = self.users[username]['score']
        health = self.users[username]['health']
        sock.send(encode({'code':'game_data', 'score':str(score), 'health':str(health), 'username':username}))

    def broadcast_content(self, sender_sock, recv_list, message_content, code='msg'):
        """
        谁给谁们说了什么, 类型是什么
        """
        # Do not send the message to server's socket and the client who has send us the message
        for sock in recv_list:
            print('recv_list: ' + str(recv_list))
            print('broadcasted content: ' + str(message_content) + ' to ' + str(self.clientsock_username[sock]))
            if sock != self.server_socket and sock != sender_sock and sock != sys.stdin and sock!=self.SYS_FAKE_SOCK:
                try:
                    response = encode(
                        {'code': code, 'content': message_content, 'sender': self.clientsock_username[sender_sock]})
                    sock.send(response)
                except Exception as e:
                    self.tackle_client_exit(sock, e.message)

    # exit series
    def tackle_client_exit(self, sock, msg="a sock exit..."):
        """an uniform client socket exit handling function"""
        print(msg)
        if self.clientsock_username.__contains__(sock):
            username = self.clientsock_username[sock]  # 计算本次在线时长(s), 并加到total_time中
            # self.users[username]['total_time'] = self.users[username]['total_time'] + (
            #     int(time.time()) - self.users[username]['login_timestamp'])
            self.users[username]['login_timestamp'] = -1  # 下线就该把login时间设置成-1
            self.users.sync()
            # self.rooms.sync()
            self.login_client_list.remove(sock)
            self.clientsock_username.pop(sock)
        self.conn_list.remove(sock)
        sock.close()

    def server_exit(self):
        global sock
        print('server admin order server to close...')
        for sock in self.conn_list:
            self.tackle_client_exit(sock)
        self.users.close()
        # self.rooms.close()
        sys.exit(0)


if __name__ == "__main__":
    server = LobbyServer(5000)
    server.loop()
