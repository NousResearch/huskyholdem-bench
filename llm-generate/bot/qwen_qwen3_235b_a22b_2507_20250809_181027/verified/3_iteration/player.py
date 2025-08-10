from typing import List, Tuple, Dict, Any
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random
import re

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 0
        self.player_hands = []
        self.blind_amount = 0
        self.big_blind_player_id = -1
        self.small_blind_player_id = -1
        self.all_players = []
        self.player_id = None
        self.is_big_blind = False
        self.is_small_blind = False
        self.position_score = 0
        self.hand_strength = 0.0
        self.strong_hole_cards = False
        self.round_num = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.player_hands = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.round_num = round_state.round_num
        if self.player_id is not None:
            self.is_big_blind = (self.player_id == self.big_blind_player_id)
            self.is_small_blind = (self.player_id == self.small_blind_player_id)
        self.strong_hole_cards = self.evaluate_hole_card_strength(self.player_hands) if self.player_hands else False
        self.hand_strength = self.estimate_hand_strength(round_state, remaining_chips)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        self.player_id = round_state.current_player[0]  # Current player's ID
        round_name = round_state.round.lower()
        current_bet = round_state.current_bet
        min_raise = round_state.min_raise
        pot = round_state.pot
        player_bet = round_state.player_bets.get(str(self.player_id), 0)
        effective_pot = pot + current_bet * len(round_state.current_player)  # Estimate total pot inflow

        # Calculate how much we need to call
        to_call = current_bet - player_bet
        can_raise = min_raise > 0 and remaining_chips >= min_raise

        # Decide action based on round and state
        if round_name == "preflop":
            action, amount = self.preflop_strategy(round_state, remaining_chips, to_call, can_raise)
        else:
            board_cards = round_state.community_cards
            hand_rank = self.evaluate_hand(self.player_hands, board_cards)
            hand_type = hand_rank[0]
            hand_score = hand_rank[1]

            # Use hand strength and position to determine post-flop actions
            if hand_score > 0.8:
                # Strong hand: raise or bet big
                if can_raise:
                    raise_amount = min(remaining_chips, max(min_raise, int(effective_pot * 0.75)))
                    return (PokerAction.RAISE, raise_amount)
                return (PokerAction.CALL, 0)
            elif hand_score > 0.5:
                # Decent hand: call or small raise
                if to_call == 0:
                    if random.random() < 0.3 and can_raise:
                        raise_amount = min(remaining_chips, max(min_raise, int(effective_pot * 0.3)))
                        return (PokerAction.RAISE, raise_amount)
                    return (PokerAction.CHECK, 0)
                elif to_call <= remaining_chips * 0.5:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            elif hand_score > 0.3:
                # Weak hand: check/fold unless cheap
                if to_call == 0:
                    return (PokerAction.CHECK, 0)
                elif to_call <= remaining_chips * 0.2:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                # Very weak hand
                if to_call == 0:
                    return (PokerAction.CHECK, 0)
                else:
                    return (PokerAction.FOLD, 0)

        # Default fallback
        if action == PokerAction.RAISE and (amount < min_raise or amount > remaining_chips):
            # Adjust invalid raise amount
            amount = max(min_raise, min(amount, remaining_chips))
        return action, amount

    def preflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, to_call: int, can_raise: bool) -> Tuple[PokerAction, int]:
        pot = round_state.pot
        effective_pot = pot + to_call * len(round_state.current_player)

        if self.strong_hole_cards:
            if to_call == 0:
                # Open raise if strong hand and no bet
                if can_raise:
                    raise_amount = min(remaining_chips, max(min(6 * self.blind_amount, effective_pot // 3), self.blind_amount * 3))
                    return (PokerAction.RAISE, raise_amount)
                return (PokerAction.CHECK, 0)
            elif to_call <= remaining_chips * 0.5:
                # Call if raise is reasonable
                return (PokerAction.CALL, 0)
            else:
                # Fold to big 3-bet with caution
                if random.random() < 0.7:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        else:
            # Weak or marginal hand
            if to_call == 0:
                return (PokerAction.CHECK, 0)
            elif to_call <= self.blind_amount:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)

    def evaluate_hole_card_strength(self, hole_cards: List[str]) -> bool:
        """ Estimate strength of hole cards using basic heuristic """
        values = [self.card_rank(card) for card in hole_cards]
        suits = [card[-1] for card in hole_cards]

        # Sort high to low
        values.sort(reverse=True)
        high_card = values[0]
        low_card = values[1]
        suited = suits[0] == suits[1]

        # Premium pairs
        if values[0] == values[1]:
            return True
        # High cards or connected
        if high_card >= 12:  # Ace or King
            if low_card >= 10 or suited:
                return True
            if high_card == 13 and low_card >= 11:  # KQ, KJ
                return True
        if high_card >= 11 and low_card >= 10 and abs(high_card - low_card) <= 1:  # Connected JTs, T9s, etc.
            return True
        return False

    def estimate_hand_strength(self, round_state: RoundStateClient, remaining_chips: int) -> float:
        """ Simple approximation of hand strength """
        if not round_state.community_cards:
            return 0.5 if self.strong_hole_cards else 0.3
        else:
            hand_rank = self.evaluate_hand(self.player_hands, round_state.community_cards)
            return hand_rank[1]

    def evaluate_hand(self, hole_cards: List[str], community_cards: List[str]) -> Tuple[int, float]:
        """ Evaluate the best 5-card poker hand and return (hand_type, score) """
        all_cards = hole_cards + community_cards
        ranks = [self.card_rank(card) for card in all_cards]
        suits = [card[-1] for card in all_cards]

        # Count rank and suit frequencies
        rank_count = {}
        suit_count = {}
        for r in ranks:
            rank_count[r] = rank_count.get(r, 0) + 1
        for s in suits:
            suit_count[s] = suit_count.get(s, 0) + 1

        # Sort by count then rank (descending)
        sorted_ranks = sorted(rank_count.items(), key=lambda x: (x[1], x[0]), reverse=True)

        # Flush check
        flush_suit = None
        for s, cnt in suit_count.items():
            if cnt >= 5:
                flush_suit = s
                break

        # Get flush cards
        flush_cards = [r for r, s in zip(ranks, suits) if s == flush_suit] if flush_suit else []

        # Sort ranks for straight check
        unique_ranks = sorted(set(ranks), reverse=True)
        if 14 in unique_ranks:  # Ace can be low for A-5 straight
            unique_ranks.append(1)

        # Check for straights
        straight_high = None
        for r in sorted(unique_ranks, reverse=True):
            if all((r-i) in unique_ranks for i in range(5)):
                straight_high = r
                break

        # Check royal and straight flush
        if flush_cards:
            flush_ranks = sorted([r for r, s in zip(ranks, suits) if s == flush_suit], reverse=True)
            for r in flush_ranks:
                if all((r-i) in flush_ranks for i in range(5)):
                    if r == 14:
                        return (9, 1.0)  # Royal Flush
                    flush_high = r
                    return (8, 0.95 + flush_high / 140)  # Straight Flush

        # Four of a kind
        if 4 in rank_count.values():
            return (7, 0.9)

        # Full house
        if 3 in rank_count.values() and 2 in rank_count.values():
            return (6, 0.8)

        # Flush
        if flush_suit and len(flush_cards) >= 5:
            return (5, 0.7)

        # Straight
        if straight_high:
            return (4, 0.6 + straight_high / 140)

        # Three of a kind
        if 3 in rank_count.values():
            return (3, 0.5)

        # Two pair
        pairs = [k for k, v in rank_count.items() if v == 2]
        if len(pairs) >= 2:
            return (2, 0.4)

        # One pair
        if len(pairs) == 1:
            return (1, 0.3)

        # High card
        return (0, 0.2 + sorted_ranks[0][0] / 140)

    def card_rank(self, card: str) -> int:
        """ Convert card string to numerical rank """
        match = re.match(r"([2-9TJQKA])([shdc])", card)
        if not match:
            return 0
        r = match.group(1)
        rank_map = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        return rank_map.get(r, int(r))

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Can be used for tracking win/loss or adjusting strategy
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Optionally log final results or clean up
        pass