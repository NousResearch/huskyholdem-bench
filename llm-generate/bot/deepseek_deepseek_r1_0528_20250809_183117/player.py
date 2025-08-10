from typing import List, Tuple, Dict, Optional
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards: Optional[List[str]] = None
        self.bb: int = 0
        self.starting_stack: int = 0
        self.all_players_ids: List[int] = []
        self.big_blinds = [
            100, 100, 100, 100, 100, 
            200, 200, 200, 200, 200,
            300, 400, 500, 600, 800,
            1000, 1200, 1600, 2000, 3000,
            4000, 5000, 6000, 8000, 10000
        ]
        self.hand_group_map = {}
        self._initialize_hand_groups()

    def _initialize_hand_groups(self):
        groups = {
            1: ['AA', 'KK', 'QQ', 'JJ', 'AKs', 'AKo'],
            2: ['TT', '99', '88', 'AQs', 'AJs', 'KQs', 'AQo'],
            3: ['77', '66', 'ATs', 'KJs', 'QJs', 'JTs', 'AJo', 'KQo'],
            4: ['55', '44', '33', '22', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KTs', 'QTs', 'J9s', 'T9s', '98s', '87s', '76s', '65s', '54s',
                'ATo', 'A9o', 'KJo', 'QJo'],
            5: ['T8s', '97s', '86s', '75s', '64s', '53s', '43s', '32s',
                'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
                'KTo', 'QTo', 'J8o', 'T8o', '98o']
        }
        self.hand_group_map = {}
        for group, hands in groups.items():
            for hand in hands:
                self.hand_group_map[hand] = group

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.bb = blind_amount
        self.starting_stack = starting_chips
        self.all_players_ids = all_players
        self.big_blinds = [
            100, 100, 100, 100, 100, 
            200, 200, 200, 200, 200,
            300, 400, 500, 600, 800,
            1000, 1200, 1600, 2000, 3000,
            4000, 5000, 6000, 8000, 10000
        ]

    def get_hand_group(self, hole_cards: List[str]) -> int:
        if hole_cards[0] == hole_cards[1]:
            rank = hole_cards[0][0]
            hand_str = f"{rank}{rank}"
        else:
            card1, card2 = hole_cards
            if card1[0] == card2[0]:
                hand_str = f"{card1[0]}{card2[0]}"
            else:
                s1 = card1[0] + card2[0]
                s2 = card2[0] + card1[0]
                hand_str = s1 if s1 in self.hand_group_map else s2
                if hand_str not in self.hand_group_map:
                    hand_str += 'o' if card1[-1] != card2[-1] else 's'
        return self.hand_group_map.get(hand_str, 6)

    def estimate_hand_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        if not community_cards:
            group = self.get_hand_group(hole_cards)
            if group == 6:
                return 0.3
            if group == 5:
                return 0.4
            if group == 4:
                return 0.5
            if group == 3:
                return 0.6
            if group == 2:
                return 0.75
            if group == 1:
                return 0.85
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            return 0.4
        return 0.5

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        current_round = round_state.round
        our_id_str = str(self.id)
        our_current_bet = round_state.player_bets.get(our_id_str, 0)
        amount_to_call = round_state.current_bet - our_current_bet
        if current_round == 'Preflop':
            group = self.get_hand_group(self.hole_cards)
            if not amount_to_call:
                if group <= 2:
                    raise_base = max(3 * self.bb, 10)
                    min_amount = round_state.min_raise
                    max_amount = min(raise_base, round_state.max_raise)
                    raise_amount = max(min_amount, min_amount)
                    return PokerAction.RAISE, raise_amount
                elif group <= 4:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0
            else:
                if group == 1 or (group == 2 and amount_to_call <= (self.bb * 2)):
                    if round_state.max_raise > 0:
                        return PokerAction.RAISE, min(round_state.min_raise, round_state.max_raise)
                    else:
                        return PokerAction.CALL, 0
                elif group == 2 and amount_to_call > (self.bb * 2) and group ==2:
                    pot_odds = amount_to_call / (round_state.pot + amount_to_call + 1e-5)
                    if pot_odds < 0.3:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0
                elif group == 3 and amount_to_call <= (self.bb):
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
        else:
            our_strength = self.estimate_hand_strength(self.hole_cards, round_state.community_cards)
            action_taken_count = len(round_state.player_actions)
            position_factor = 0.1 * min(action_taken_count, 4)
            hand_rank_factor = our_strength + position_factor

            min_raise = round_state.min_raise
            max_raise = round_state.max_raise

            if amount_to_call == 0:
                if hand_rank_factor >= 0.6:
                    if round_state.max_raise > 0 and min_raise < remaining_chips * 0.5:
                        raise_amount = min(max_raise, max(int(min_raise * 1.5), min_raise))
                        return PokerAction.RAISE, raise_amount
                    else:
                        return PokerAction.CHECK, 0
                else:
                    return PokerAction.CHECK, 0
            elif amount_to_call > 0:
                pot_odds = amount_to_call / (amount_to_call + round_state.pot + 1e-5)
                if hand_rank_factor > pot_odds + 0.2:
                    if round_state.min_raise > 0 and round_state.min_raise < remaining_chips * 0.6:
                        return PokerAction.RAISE, min_raise
                    else:
                        return PokerAction.CALL, 0
                elif hand_rank_factor > pot_odds:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
        return PokerAction.CHECK, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass