from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import itertools

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.parsed_hole = []
        self.big_blind = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.parsed_hole = self.parse_cards(player_hands)
        self.big_blind = blind_amount

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        if self.id is None:
            return PokerAction.FOLD, 0

        my_id = str(self.id)
        my_bet = round_state.player_bets.get(my_id, 0)
        to_call = round_state.current_bet - my_bet
        pot = round_state.pot
        effective_stack = remaining_chips
        min_raise_by = round_state.min_raise
        phase = round_state.round

        if phase == 'Preflop':
            strength = self.get_preflop_strength(self.parsed_hole)
        else:
            hand_type, _ = self.get_hand_type(self.hole_cards, round_state.community_cards)
            strength = hand_type / 10.0

        num_active = len(round_state.current_player)
        strength /= max(1, num_active - 1) * 0.5 + 0.5  # adjust for number of players

        if to_call > effective_stack:
            if strength > 0.5 and effective_stack > 0:
                return PokerAction.ALL_IN, 0
            else:
                return PokerAction.FOLD, 0

        if to_call == 0:
            if strength > 0.7:
                raise_amount = int(0.75 * pot) + self.big_blind
                if raise_amount < min_raise_by:
                    raise_amount = min_raise_by
                if raise_amount > effective_stack:
                    if effective_stack > 0 and strength > 0.6:
                        return PokerAction.ALL_IN, 0
                    else:
                        return PokerAction.CHECK, 0
                return PokerAction.RAISE, raise_amount
            else:
                return PokerAction.CHECK, 0
        else:
            pot_odds = to_call / (pot + to_call + 0.0001)
            if strength > pot_odds + 0.3:
                raise_amount = int(pot * 1.0) + to_call
                min_raise_by_total = to_call + min_raise_by
                if raise_amount < min_raise_by_total:
                    raise_amount = min_raise_by_total
                if raise_amount > effective_stack:
                    if strength > pot_odds + 0.1 and effective_stack > 0:
                        return PokerAction.ALL_IN, 0
                    else:
                        return PokerAction.FOLD, 0
                return PokerAction.RAISE, raise_amount
            elif strength > pot_odds:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass

    def parse_card(self, card: str) -> Tuple[int, str]:
        rank_str = card[0]
        suit = card[1]
        if rank_str.isdigit():
            rank = int(rank_str)
        else:
            rank_map = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
            rank = rank_map[rank_str]
        return rank, suit

    def parse_cards(self, cards: List[str]) -> List[Tuple[int, str]]:
        return [self.parse_card(c) for c in cards]

    def get_preflop_strength(self, hole: List[Tuple[int, str]]) -> float:
        if len(hole) != 2:
            return 0.0
        r1, s1 = hole[0]
        r2, s2 = hole[1]
        if r1 < r2:
            r1, r2 = r2, r1
        suited = s1 == s2
        if r1 == r2:
            return max(0.5, (r1 - 2) / 12.0 * 0.5 + 0.5)
        else:
            delta = r1 - r2
            base = (r1 + r2) / 28.0 * 0.5
            if suited:
                base += 0.15
            if delta <= 2:
                base += (3 - delta) * 0.05
            if r1 == 14:
                base += 0.25 if r2 >= 11 else 0.15
            elif r1 == 13 and r2 >= 11:
                base += 0.1
            return min(0.85, base)

    def evaluate_five(self, five: List[Tuple[int, str]]) -> Tuple[int, List[int]]:
        ranks = sorted([r for r, s in five], reverse=True)
        suits = [s for r, s in five]
        count = {}
        for r in ranks:
            count[r] = count.get(r, 0) + 1
        is_flush = len(set(suits)) == 1
        is_straight = len(set(ranks)) == 5 and (ranks[0] - ranks[4] == 4)
        straight_high = ranks[0]
        if ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5
        if is_flush and is_straight:
            if straight_high == 14:
                return 10, [14]
            return 9, [straight_high]
        if 4 in count.values():
            quad = next(r for r, c in count.items() if c == 4)
            kicker = next(r for r, c in count.items() if c == 1)
            return 8, [quad, kicker]
        if 3 in count.values() and 2 in count.values():
            trip = next(r for r, c in count.items() if c == 3)
            pair = next(r for r, c in count.items() if c == 2)
            return 7, [trip, pair]
        if is_flush:
            return 6, ranks
        if is_straight:
            return 5, [straight_high]
        if 3 in count.values():
            trip = next(r for r, c in count.items() if c == 3)
            kickers = sorted([r for r, c in count.items() if c == 1], reverse=True)
            return 4, [trip] + kickers
        pair_counts = list(count.values()).count(2)
        if pair_counts == 2:
            pairs = sorted([r for r, c in count.items() if c == 2], reverse=True)
            kicker = next(r for r, c in count.items() if c == 1)
            return 3, pairs + [kicker]
        if 2 in count.values():
            pair = next(r for r, c in count.items() if c == 2)
            kickers = sorted([r for r, c in count.items() if c == 1], reverse=True)
            return 2, [pair] + kickers
        return 1, ranks

    def get_hand_type(self, hole: List[str], community: List[str]) -> Tuple[int, List[int]]:
        total_cards = self.parse_cards(hole + community)
        n = len(total_cards)
        if n < 5:
            return 0, []
        best_type = 0
        best_tie = []
        combos = itertools.combinations(total_cards, 5) if n > 5 else [total_cards]
        for five in combos:
            t, tie = self.evaluate_five(list(five))
            if t > best_type or (t == best_type and tie > best_tie):
                best_type = t
                best_tie = tie
        return best_type, best_tie