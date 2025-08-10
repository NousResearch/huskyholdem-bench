from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = None
        self.big_blind = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.big_blind = blind_amount

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        my_id_str = str(self.id)
        my_bet = round_state.player_bets.get(my_id_str, 0)
        to_call = round_state.current_bet - my_bet

        if round_state.round == 'Preflop':
            strength = self._hand_strength()
            if to_call > 0:
                if strength > 20:
                    amount = max(round_state.min_raise, 3 * self.big_blind)
                    amount = min(amount, round_state.max_raise)
                    return PokerAction.RAISE, amount
                elif strength > 15 and to_call <= self.big_blind:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
            else:
                if strength > 20:
                    amount = max(round_state.min_raise, 3 * self.big_blind)
                    amount = min(amount, round_state.max_raise)
                    return PokerAction.RAISE, amount
                else:
                    return PokerAction.CHECK, 0
        else:
            if to_call == 0:
                return PokerAction.CHECK, 0
            elif to_call <= 2 * self.big_blind:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass

    def _card_rank(self, card: str) -> int:
        r = card[0]
        if r == 'A': return 14
        if r == 'K': return 13
        if r == 'Q': return 12
        if r == 'J': return 11
        if r == 'T': return 10
        return int(r)

    def _hand_strength(self) -> int:
        if not self.hole_cards or len(self.hole_cards) != 2:
            return 0
        c1, c2 = self.hole_cards
        r1 = self._card_rank(c1)
        r2 = self._card_rank(c2)
        suited = 2 if c1[1] == c2[1] else 0
        pair = 5 if r1 == r2 else 0
        return r1 + r2 + suited + pair