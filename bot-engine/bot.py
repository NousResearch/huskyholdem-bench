from abc import ABC, abstractmethod
from typing import List, Tuple

from type.round_state import RoundStateClient
from type.poker_action import PokerAction

class Bot(ABC):
    def __init__(self) -> None:
        """ Initializes the player. """
        self.id = None
        pass

    def set_id(self, player_id: int) -> None:
        """ Sets the player ID. """
        self.id = player_id

    @abstractmethod
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]) -> None:
        """ Called when the game starts. """
        pass

    @abstractmethod
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        """ Called at the start of each round. """
        pass

    @abstractmethod
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Called when it is the player's turn to act. """
        pass

    @abstractmethod
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        """ Called at the end of each round. """
        pass

    @abstractmethod
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict) -> None:
        """ Called at the end of the game. """
        pass