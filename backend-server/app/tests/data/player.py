
from typing import List
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        print("Player called on game start")
        print("Player hands: ", player_hands)
        print("Blind: ", blind_amount)
        print("Big blind player id: ", big_blind_player_id)
        print("Small blind player id: ", small_blind_player_id)
        print("All players in game: ", all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        print("Player called on round start")
        print("Round state: ", round_state)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int):
        """ Returns the action for the player. """
        print("Player called get action")

        raised = False
        for player_action in round_state.player_actions.values():
            if player_action == "Raise":
                raised = True
                break

        if not raised and round_state.round_num == 1:
            return PokerAction.RAISE, 100
        
        if round_state.current_bet == 0:
            return PokerAction.CHECK, 0
        
        amount_to_call = round_state.current_bet - round_state.player_bets[str(self.id)]
        return PokerAction.CALL, amount_to_call

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        print("Player called on end round")

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        print("Player called on end game, with player score: ", player_score)
        print("All final scores: ", all_scores)
        print("Active players hands: ", active_players_hands)