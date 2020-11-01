import socket
from threading import Thread
from json import loads, dumps
import PySimpleGUI as sg


def listen_from_socket(socket_listener, window):
    while True:
        # Receive any data the server sends on connection
        data_from_socket = socket_listener.recv(2048).decode()
        message_json = loads(data_from_socket)

        if message_json['action'] == 'disconnect_confirmation':
            return

        if len(data_from_socket) > 0:
            print(f'[Data received from socket] {data_from_socket}')
            if message_json['action'] == 'new_message':
                window['-CHATBOX-'].print(f'<{message_json["from"]}> {message_json["message"]}')


def main():
    # Window theme
    sg.theme('Dark Blue 3')

    # Window layout for the username window
    username_layout = [
        [sg.Text('Welcome to ClassChat!')],
        [sg.Text('Username:')],
        [sg.InputText()],
        [sg.Submit(), sg.Cancel()]
    ]

    # Present the window to the user
    window = sg.Window('ClassChat Login', username_layout)
    event, values = window.read()
    window.close()

    # Retrieve the username
    username = values[0]

    # Main window layout
    main_layout = [
        [sg.Text('Chat', size=(152, 1)), sg.Text('Users')],
        [
            sg.Multiline(size=(150, 50), disabled=True, autoscroll=True, key="-CHATBOX-", write_only=True),
            sg.Multiline(size=(20, 50), disabled=True, key="-USERLIST-", write_only=True)
        ],
        [sg.InputText(size=(152, 1)), sg.Button('Send ->'), sg.Button('Exit')]
    ]

    window = sg.Window(f'ClassChat - connected as {username}', main_layout, finalize=True)

    # Create socket
    communication_socket = socket.socket()

    # Attempt a connection on port 8080
    communication_socket.connect(('127.0.0.1', 8080))

    message_json = dumps({
        'action': 'connection_event',
        'from': username
    })
    communication_socket.send(message_json.encode())

    # Spawn the listener thread
    thread = Thread(target=listen_from_socket, args=[communication_socket, window])
    thread.start()

    while True:
        event, values = window.read()
        print(event, values)

        # If the exit button is pressed or the window is closed, stop gracefully
        if event == sg.WIN_CLOSED or event == 'Exit':
            # Say goodbye to the server!
            message_json = dumps({
                'action': 'disconnect_event',
                'from': username
            })
            communication_socket.send(message_json.encode())
            communication_socket.close()

            # Kill the listener thread
            thread.join()

            # Break our main loop
            break
        if event == 'Send ->':
            message_json = dumps({
                'action': 'send_to_server',
                'from': username,
                'message': values[0]
            })
            communication_socket.send(message_json.encode())

    window.close()


main()
