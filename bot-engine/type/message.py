from enum import Enum

class MessageType(Enum):
    CONNECT = 0
    DISCONNECT = 1
    GAME_START = 2
    ROUND_START = 3
    REQUEST_PLAYER_ACTION = 4
    PLAYER_ACTION = 5
    ROUND_END = 6
    GAME_END = 7
    TIME_STAMPT = 8
    GAME_STATE = 9
    MESSAGE = 10