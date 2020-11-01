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

        if message_json['action'] == 'connect_confirmation':
            user_list = '\n'.join(message_json['online_users'])
            window['-USERLIST-'].print(user_list)

        if message_json['action'] == 'user_list_update':
            window['-USERLIST-'].update('')
            active_users = '\n'.join(message_json['users'])
            window['-USERLIST-'].print(active_users)

        if message_json['action'] == 'direct_message':
            window['-CHATBOX-'].print(f'< {message_json["from"]} -> You > {message_json["message"]}')

        if message_json['action'] == 'command_failed':
            window['-CHATBOX-'].print(f'! Command Failed ! {message_json["error"]}')

        if message_json['action'] == 'direct_message_confirmation':
            window['-CHATBOX-'].print(f'< You -> {message_json["to"]} > {message_json["message"]}')

        if len(data_from_socket) > 0:
            print(f'[Data received from socket] {data_from_socket}')
            if message_json['action'] == 'new_message':
                window['-CHATBOX-'].print(f'< {message_json["from"]} > {message_json["message"]}')


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
        [sg.InputText(size=(152, 1), key="-INPUTBOX-"), sg.Button('Send ->', bind_return_key=True), sg.Button('Exit')]
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
            # Don't allow blank messages to be sent
            if values['-INPUTBOX-'] == '':
                continue

            # Clear our inputbox
            window['-INPUTBOX-'].update('')

            # Check if we are dealing with a command
            if values['-INPUTBOX-'][0] == '/':
                split_message = values['-INPUTBOX-'].split(' ')
                command = split_message[0].split('/')[1]
                del split_message[0]

                if command == 'msg' or command == 'message':
                    if len(split_message) != 2:
                        window['-CHATBOX-'].print('Invalid amount of arguments required, message accepts exactly 2.')
                        continue
                    if len(split_message[0]) == 0:
                        window['-CHATBOX-'].print('You must supply a username to send a message to.')
                        continue
                    if len(split_message[1]) == 0:
                        window['-CHATBOX-'].print('You must supply a message.')
                        continue
                else:
                    window['-CHATBOX-'].print('Unknown command.')
                    continue

                message_json = dumps({
                    'action': 'command',
                    'from': username,
                    'command': command,
                    'args': split_message
                })
            else:
                message_json = dumps({
                    'action': 'send_to_server',
                    'from': username,
                    'message': values['-INPUTBOX-']
                })
            communication_socket.send(message_json.encode())

    window.close()


main()
