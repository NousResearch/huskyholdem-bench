from dataclasses import dataclass
from enum import Enum
import json
from typing import List, Dict

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

@dataclass
class GameStateMessage():
    round_num: int
    round: str
    community_cards: List
    pot: int
    current_player: int
    current_bet: int
    min_raise: int
    max_raise: int
    player_bets: Dict[int, int]
    player_actions: Dict[int, str]
    player_money: Dict[int, int] = None  # New field for player money
    side_pots: List[Dict] = None  # New field for side pot information

@dataclass
class RequestPlayerActionMessage():
    player_id: int
    time_left: int