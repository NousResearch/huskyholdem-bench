"""
Warning: this file needs to always be in sync with the game engine server.
The game engine server uses this file to determine the message types and their corresponding names.
"""

from enum import Enum

class PokerAction(Enum):
    FOLD = 1
    CHECK = 2
    CALL = 3
    RAISE = 4
    ALL_IN = 5

class PokerRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3