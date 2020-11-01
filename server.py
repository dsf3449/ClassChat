import socket
import queue
from datetime import datetime
from threading import Thread
from json import loads, dumps
from time import sleep


def new_connection_listener(communication_socket, active_connection_queue, message_queue):
    # Listen for connections
    while True:
        # Check for a connection, if available, accept it.
        client, address = communication_socket.accept()
        print(f'Connection received from {address}.')

        # Spawn a data listener thread
        new_thread = Thread(target=data_listener, args=[client, message_queue, active_connection_queue])
        new_thread.start()

        # Respond
        client.send(dumps({
            'action': 'connect_confirmation',
            'from': 'server',
            'server_time': str(datetime.now())
        }).encode())


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
    thread = Thread(target=new_connection_listener, args=[communication_socket, active_connection_queue, message_queue])
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

            if message_json['action'] == 'send_to_server':
                print('sending new message to clients')
                for username in active_connection_dict:
                    active_connection_dict[username].send(dumps({
                        'action': 'new_message',
                        'from': message_json['from'],
                        'message': message_json['message']
                    }).encode())


main()
