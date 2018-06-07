import select
import socket
import time
from math import ceil
from enum import IntEnum, unique

"""
Send types:
    - :message
    - :error
    - :vote
    - :endvote
    - :
"""


@unique
class ServerOpCodes(IntEnum):
    """OpCodes sent by the server"""
    gamestart = 0
    message = 1  # informational
    pm = 2  # private p2p message
    error = 3
    card = 4  # assign cards
    vote = 5  # team select vote
    endvote = 6  # win / loss data
    setleader = 7  # leader changed (turn change or vote loss)
    teamadd = 8  # leader updates team
    teamremove = 9  # leader updates team
    getcard = 10  # get a success/fail card from users anonymously
    missiondone = 11  # mission end + results
    getname = 12


@unique
class ClientOpCodes(IntEnum):
    """OpCodes sent by the client"""
    name = 0
    message = 1
    sendpm = 2
    approve = 3
    reject = 4
    teamadd = 5
    teamremove = 6
    success = 7
    fail = 8


# nspies = math.ceil(nplayers / 3)

class Game:
    connected = None
    usernames = None
    nspies = None

    def __init__(self, maxconnections, connect_timeout, username_timeout, host='0.0.0.0', port=5555):
        self.maxconnections = maxconnections
        self.connect_timeout = connect_timeout
        self.username_timeout = username_timeout
        self.host = host
        self.port = port
        self.processors = {}
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # A generic listening socket
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        connection.bind((host, port))  # Hosts by default on 0.0.0.0:5555
        connection.listen(maxconnections)  # Can only listen for maxconnections
        self.socket = connection

        self.await_connect()
        self.await_usernames()

    def start(self):
        self.nspies = ceil(len(self.usernames) / 3)

    def close(self):
        for sock in self.connected:
            sock.close()
        self.socket.close()

    def get_next(self, sock):
        while True:
            message = sock.recv(1024)
            messages = message.split("\n")
            for message in messages:
                message = message.decode()
                code = ord(message[0])
                yield code, message.strip()

    def await_connect(self):
        """Wait for users to connect, max users"""
        stime = time.monotonic()  # Monotonic is cool
        self.connected = []
        timeout = self.connect_timeout
        while len(self.connected) != self.maxconnections:
            rr, wr, er = select.select([self.socket], [], [], timeout * 1000)
            if rr:
                sock, (addr, port) = rr[0].accept()
                self.connected.append(sock)
                for user in self.connected:
                    self.send_user(user, f"{addr}:{port} connected!")
            timeout = timeout - (stime - time.monotonic())
            if timeout <= 0:  # We break when timeout is reached with whatever players connected
                break
        if not self.connected:
            raise TimeoutError("Nobody connected!")  # If nobody connects just raise

    def await_usernames(self):
        self.named = dict()
        stime = time.monotonic()
        cnum = len(self.connected)
        timeout = self.username_timeout
        for user in self.connected:
            self.send_opcode(user, ServerOpCodes.getname, "Choose your name")

        while len(self.named) < cnum:
            rr, wr, er = select.select(self.connected, [], [], timeout * 1000)
            timeout = timeout - (stime - time.monotonic())

            for sock in rr:
                name = next(self.processors[sock])
                if name in self.named.items():
                    self.send_user(sock, "That name is already taken!")
                    self.send_opcode(sock, ServerOpCodes.name, "Pick a new name!")
                    continue
                self.named[sock] = name
                addr, port = sock.getsockname()
                self.broadcast(f"{addr}:{port} has chosen name {name}!")
                self.connected.remove(sock)  # No need to wait anymore, we have their name

            if timeout <= 0:
                break

        if not self.named:
            raise TimeoutError("Nobody sent a name!")

        for sock in self.connected:  # If someone doesnt connect in time, we just close the connection
            self.send_opcode(sock, ServerOpCodes.error, "You didn't send a name in time!")
            sock.close()

        for sock in self.named:
            self.processors[sock] = self.get_next(sock)

    def broadcast(self, *message):
        """Send a message to all connected, varargs are connected with a space like print"""
        for user in self.named.keys():
            self.send_user(user, *message)

    def broadcast_opcode(self, opcode, *message):
        """Send an opcode to all users"""
        for user in self.named.keys():
            self.send_opcode(user, opcode, *message)

    def send_user(self, user, *message):
        """Send a message to a single socket"""
        self.send_opcode(user, ServerOpCodes.message, *message)

    def send_opcode(self, user, opcode, *message):
        message = " ".join(message)
        user.send(chr(opcode).encode() + message.encode() + b"\n")