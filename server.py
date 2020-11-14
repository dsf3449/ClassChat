import socket
import queue
from datetime import datetime
from threading import Thread
from json import loads, dumps


def new_connection_listener(communication_socket, active_connection_queue, message_queue, active_connection_dict):
    # Listen for connections
    while True:
        # Check for a connection, if available, accept it.
        client, address = communication_socket.accept()
        print(f'Connection received from {address}.')

        # Spawn a data listener thread
        new_thread = Thread(target=data_listener, args=[client, message_queue, active_connection_queue])
        new_thread.start()

        online_users = get_list_of_active_users(active_connection_dict)

        # JSON to return to client
        json_response = {
            'action': 'connect_confirmation',
            'from': 'server',
            'server_time': str(datetime.now()),
            'online_users': online_users
        }

        # Respond
        client.send(dumps(json_response).encode())


def data_listener(communication_socket, message_queue, active_connection_queue):
    while True:
        data_from_socket = communication_socket.recv(2048).decode()

        message_json = loads(data_from_socket)

        if message_json['action'] == "connection_event":
            # Add to our active session list
            active_connection_queue.put((communication_socket, message_json['from']))

        if message_json['action'] == "disconnect_event":
            message_queue.put(data_from_socket)
            return

        if len(data_from_socket) > 0:
            print(f'[Data received from socket] {data_from_socket}')
            message_queue.put(data_from_socket)


def fetch_connections_from_queue(thread_queue, connection_list):
    while not thread_queue.empty():
        session = thread_queue.get()
        connection_list[session[1]] = session[0]

    return connection_list


def get_list_of_active_users(active_connection_dict):
    active_users = []
    for user in active_connection_dict:
        active_users.append(user)

    return active_users


def dispatch_to_all_clients(active_connection_dict, json_object):
    for username in active_connection_dict:
        active_connection_dict[username].send(dumps(json_object).encode())


def main():
    # Create socket
    communication_socket = socket.socket()

    # Bind address & port
    communication_socket.bind(('127.0.0.1', 8080))

    # We want to reject more than 5 connections
    communication_socket.listen(5)

    # Queue where we will store our active connections
    active_connection_queue = queue.Queue()

    # Dict where we will store our active connections
    active_connection_dict = {}

    # Queue where we will store messages to dispatch
    message_queue = queue.Queue()

    # Spawn the connection listener thread
    thread = Thread(target=new_connection_listener, args=[communication_socket, active_connection_queue, message_queue, active_connection_dict])
    thread.start()

    while True:
        active_connection_dict = fetch_connections_from_queue(active_connection_queue, active_connection_dict)
        if not message_queue.empty():
            message = message_queue.get()
            message_json = loads(message)

            if message_json['action'] == 'disconnect_event':
                socket_to_close = active_connection_dict.pop(message_json['from'])
                socket_to_close.send(dumps({'action': 'disconnect_confirmation', 'from': 'server'}).encode())
                socket_to_close.close()

                active_users = get_list_of_active_users(active_connection_dict)

                dispatch_to_all_clients(active_connection_dict, {
                        'action': 'user_list_update',
                        'from': 'server',
                        'users': active_users
                    })

            if message_json['action'] == 'send_to_server':
                print('sending new message to clients')
                dispatch_to_all_clients(active_connection_dict, {
                        'action': 'new_message',
                        'from': message_json['from'],
                        'message': message_json['message']
                    })

            if message_json['action'] == 'connection_event':
                print('refreshing client lists')

                active_users = get_list_of_active_users(active_connection_dict)

                dispatch_to_all_clients(active_connection_dict, {
                        'action': 'user_list_update',
                        'from': 'server',
                        'users': active_users
                    })

            if message_json['action'] == 'command':
                if message_json['command'] == 'msg' or message_json['command'] == 'message':
                    if message_json['args'][0] in active_connection_dict:
                        user_to_dm = message_json['args'].pop(0)
                        message_to_dm = " ".join(message_json['args'])
                        socket_to_dm = active_connection_dict[user_to_dm]
                        dm = dumps({
                            'action': 'direct_message',
                            'from': message_json['from'],
                            'message': message_to_dm
                        })
                        socket_to_dm.send(dm.encode())

                        active_connection_dict[message_json['from']].send(dumps({
                            'action': 'direct_message_confirmation',
                            'to': user_to_dm,
                            'message': message_to_dm
                        }).encode())
                    else:
                        active_connection_dict[message_json['from']].send(dumps({
                            'action': 'command_failed',
                            'error': 'The user you are trying to message is not online.'
                        }).encode())


main()
