from typing import List, Tuple, Dict
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.player_hands = {}
        self.big_blind_amount = 0
        self.small_blind_amount = 0
        self.big_blind_player_id = None
        self.small_blind_player_id = None
        self.all_players = []
        self.strong_hole_cards = False
        self.positional_advantage = False
        self.game_stage = None
        self.starting_chips = 0
        self.hand_history = []

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.big_blind_amount = blind_amount
        self.small_blind_amount = blind_amount // 2
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players
        self.player_hands = {str(pid): None for pid in all_players}
        for pid, card in player_hands:
            self.player_hands[str(pid)] = card

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.game_stage = round_state.round
        my_id = str(self.id)
        if my_id in self.player_hands and self.player_hands[my_id]:
            hole_cards = self.player_hands[my_id]
            self.strong_hole_cards = self.evaluate_hole_card_strength(hole_cards)
        else:
            self.strong_holes_cards = False
        self.positional_advantage = self.is_in_late_position(round_state, my_id)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        my_id = str(self.id)
        current_bet = round_state.current_bet
        min_raise = round_state.min_raise
        max_raise = round_state.max_raise
        my_current_bet = round_state.player_bets.get(my_id, 0)
        pot_size = round_state.pot
        num_community_cards = len(round_state.community_cards)
        
        # Default fallback action
        action = PokerAction.FOLD
        amount = 0

        # Check if we can check
        can_check = (current_bet == my_current_bet)
        
        # Determine hand strength based on game phase
        hand_strength = self.assess_hand_strength(my_id, round_state, remaining_chips)

        # Preflop strategy
        if num_community_cards == 0:
            if self.strong_hole_cards:
                if can_check:
                    action = PokerAction.RAISE
                    amount = min(max_raise, max(min_raise, pot_size // 2))
                else:
                    if current_bet - my_current_bet <= remaining_chips * 0.1:
                        action = PokerAction.CALL
                    else:
                        action = PokerAction.RAISE
                        amount = min(max_raise, current_bet - my_current_bet + min(pot_size // 2, max_raise))
            else:
                if can_check:
                    action = PokerAction.CHECK
                else:
                    action = PokerAction.FOLD

        # Post-flop strategies
        elif num_community_cards in [3, 4, 5]:
            draw_potential = self.has_draw_potential(round_state, my_id)
            made_hand = hand_strength > 0.5
            is_aggressive_betting = current_bet > pot_size * 0.3

            if made_hand:
                if can_check:
                    action = PokerAction.RAISE
                    amount = min(max_raise, pot_size)
                else:
                    if is_aggressive_betting:
                        action = PokerAction.CALL
                    else:
                        raise_amount = current_bet - my_current_bet + max(min_raise, pot_size)
                        action = PokerAction.RAISE
                        amount = min(max_raise, raise_amount)
            elif draw_potential and remaining_chips > 100:
                if can_check or (current_bet - my_current_bet) <= pot_size * 0.2:
                    action = PokerAction.CALL
                else:
                    action = PokerAction.FOLD
            else:
                if can_check:
                    action = PokerAction.CHECK
                else:
                    action = PokerAction.FOLD

        # All-in protection
        if action == PokerAction.RAISE:
            if amount <= 0:
                amount = min_raise if min_raise <= max_raise else max_raise
            if amount < min_raise:
                amount = min_raise
            if amount > max_raise:
                amount = max_raise
            if amount >= remaining_chips:
                action = PokerAction.ALL_IN
                amount = remaining_chips

        # Fallback safety
        if action == PokerAction.CALL:
            call_amount = current_bet - my_current_bet
            if call_amount >= remaining_chips:
                action = PokerAction.ALL_IN
            elif call_amount <= 0:
                action = PokerAction.CHECK
        elif action == PokerAction.RAISE and amount < min_raise:
            action = PokerAction.CALL

        return action, amount

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        self.hand_history.append({
            'round_num': round_state.round_num,
            'round': round_state.round,
            'pot': round_state.pot,
            'chips': remaining_chips,
            'actions': dict(round_state.player_actions)
        })

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass

    def is_in_late_position(self, round_state: RoundStateClient, player_id: str) -> bool:
        acting_players = round_state.current_player
        try:
            player_idx = acting_players.index(int(player_id))
            return player_idx >= len(acting_players) - 2
        except Exception:
            return False

    def assess_hand_strength(self, player_id: str, round_state: RoundStateClient, remaining_chips: int) -> float:
        hole_cards = self.player_hands.get(player_id, [])
        if not hole_cards:
            return 0.0
        community_cards = round_state.community_cards
        all_cards = hole_cards + community_cards
        hand_rank = self.evaluate_hand_rank(all_cards)
        return hand_rank / 9.0  # Normalize to 0-1 scale

    def evaluate_hand_rank(self, cards: List[str]) -> int:
        # Simplified hand evaluation: only does basic checks
        if len(cards) < 5:
            return self.evaluate_hole_card_strength(cards)
        
        values = [self.card_to_value(c[0]) for c in cards]
        suits = [c[1] for c in cards]
        value_counts = {v: values.count(v) for v in set(values)}
        suit_counts = {s: suits.count(s) for s in set(suits)}

        is_flush = max(suit_counts.values()) >= 5
        sorted_values = sorted(set(values), reverse=True)
        is_straight = False
        for i in range(len(sorted_values) - 4):
            if sorted_values[i] - sorted_values[i+4] == 4:
                is_straight = True
                break
        if 14 in sorted_values and 2 in sorted_values and 3 in sorted_values and 4 in sorted_values and 5 in sorted_values:
            is_straight = True

        has_four = 4 in value_counts.values()
        has_three = 3 in value_counts.values()
        pairs = list(value_counts.values()).count(2)
        has_two_pair = pairs >= 2
        has_pair = pairs == 1

        if is_straight and is_flush:
            return 8  # Straight flush
        elif has_four:
            return 7  # Four of a kind
        elif has_three and has_pair:
            return 6  # Full house
        elif is_flush:
            return 5  # Flush
        elif is_straight:
            return 4  # Straight
        elif has_three:
            return 3  # Three of a kind
        elif has_two_pair:
            return 2  # Two pair
        elif has_pair:
            return 1  # One pair
        else:
            return 0  # High card

    def has_draw_potential(self, round_state: RoundStateClient, player_id: str) -> bool:
        hole_cards = self.player_hands.get(player_id, [])
        if not hole_cards:
            return False
        all_cards = hole_cards + round_state.community_cards
        values = [self.card_to_value(c[0]) for c in all_cards]
        suits = [c[1] for c in all_cards]
        
        # Flush draw: 4 cards of same suit
        suit_count = {s: suits.count(s) for s in suits}
        if max(suit_count.values()) >= 4:
            return True
        
        # Open-ended straight draw
        value_set = set(values)
        for v in value_set:
            if (v + 1 in value_set and v + 2 in value_set and v + 3 in value_set) or \
               (v - 1 in value_set and v - 2 in value_set and v - 3 in value_set):
                return True

        return False

    def evaluate_hole_card_strength(self, hole_cards: List[str]) -> bool:
        if not hole_cards or len(hole_cards) < 2:
            return False
        try:
            v1 = self.card_to_value(hole_cards[0][0])
            v2 = self.card_to_value(hole_cards[1][0])
            s1 = hole_cards[0][1]
            s2 = hole_cards[1][1]

            # High pairs: TT, JJ, QQ, KK, AA
            if v1 == v2 and v1 >= 10:
                return True
            # High cards suited
            if max(v1, v2) >= 11 and s1 == s2:
                return True
            # Both high cards (broadway)
            if v1 >= 10 and v2 >= 10:
                return True
            # One high with connector
            if (v1 >= 10 or v2 >= 10) and abs(v1 - v2) == 1:
                return True
            return False
        except Exception:
            return False

    def card_to_value(self, card_rank: str) -> int:
        rank_map = {'A': 14, 'K': 13, 'Q': 12, 'J': 11}
        return rank_map.get(card_rank, int(card_rank) if card_rank.isdigit() else 2)