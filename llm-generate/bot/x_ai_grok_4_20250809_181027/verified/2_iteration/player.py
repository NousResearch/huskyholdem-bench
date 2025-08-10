from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from collections import Counter
from itertools import combinations

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = None
        self.small_blind = 0
        self.big_blind = 0
        self.all_players = []

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.small_blind = blind_amount
        self.big_blind = 2 * blind_amount
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def parse_card(self, card: str) -> Tuple[int, str]:
        rank_str = card[0]
        suit = card[1]
        ranks = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        return ranks[rank_str], suit

    def chen_score(self, card1: str, card2: str) -> int:
        r1, s1 = self.parse_card(card1)
        r2, s2 = self.parse_card(card2)
        if r1 < r2:
            r1, r2 = r2, r1
        if r1 == 14:
            high_score = 10
        elif r1 == 13:
            high_score = 8
        elif r1 == 12:
            high_score = 7
        elif r1 == 11:
            high_score = 6
        else:
            high_score = r1 / 2.0
        pair = r1 == r2
        if pair:
            score = high_score * 2
            if score < 5:
                score = 5
        else:
            score = high_score
        suited = s1 == s2
        if suited:
            score += 2
        gap = r1 - r2
        if gap <= 1:
            score += 1
        elif gap == 3:
            score -= 1
        elif gap >= 4:
            score -= 2
        if gap <= 2 and r1 < 12 and r2 < 12:
            score += 1
        return round(score)

    def evaluate_hand(self, cards: List[Tuple[int, str]]) -> Tuple[int, List[int]]:
        ranks = sorted([c[0] for c in cards], reverse=True)
        suits = [c[1] for c in cards]
        flush = len(set(suits)) == 1
        unique_ranks = sorted(set(ranks), reverse=True)
        straight = False
        if len(unique_ranks) == 5:
            if unique_ranks[0] - unique_ranks[4] == 4:
                straight = True
            elif set(unique_ranks) == {14, 5, 4, 3, 2}:
                straight = True
        if flush and straight:
            if unique_ranks == [14, 5, 4, 3, 2]:
                return 8, [5, 4, 3, 2, 1]
            return 8, unique_ranks
        rank_count = Counter(ranks)
        counts = sorted(rank_count.values(), reverse=True)
        if counts[0] == 4:
            quad_rank = [r for r, c in rank_count.items() if c == 4][0]
            kicker = sorted([r for r in ranks if r != quad_rank], reverse=True)[0]
            return 7, [quad_rank, kicker]
        if counts == [3, 2]:
            trip_rank = [r for r, c in rank_count.items() if c == 3][0]
            pair_rank = [r for r, c in rank_count.items() if c == 2][0]
            return 6, [trip_rank, pair_rank]
        if flush:
            return 5, ranks
        if straight:
            if set(unique_ranks) == {14, 5, 4, 3, 2}:
                return 4, [5, 4, 3, 2, 1]
            return 4, unique_ranks
        if counts[0] == 3:
            trip_rank = [r for r, c in rank_count.items() if c == 3][0]
            kickers = sorted([r for r in ranks if r != trip_rank], reverse=True)
            return 3, [trip_rank] + kickers
        if counts[:2] == [2, 2]:
            pair_ranks = sorted([r for r, c in rank_count.items() if c == 2], reverse=True)
            kicker = [r for r in ranks if r not in pair_ranks][0]
            return 2, pair_ranks + [kicker]
        if counts[0] == 2:
            pair_rank = [r for r, c in rank_count.items() if c == 2][0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return 1, [pair_rank] + kickers
        return 0, ranks

    def get_best_hand(self, available: List[str]) -> Tuple[int, List[int]]:
        parsed = [self.parse_card(c) for c in available]
        if len(parsed) < 5:
            return (0, [])
        hands = []
        for combo in combinations(parsed, 5):
            hands.append(self.evaluate_hand(list(combo)))
        return max(hands, key=lambda h: (h[0], tuple(h[1])))

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        my_id_str = str(self.id)
        my_bet = round_state.player_bets.get(my_id_str, 0)
        to_call = round_state.current_bet - my_bet
        min_r = round_state.min_raise
        max_r = round_state.max_raise
        pot = round_state.pot + 0.0001  # avoid divide by zero
        score = self.chen_score(self.hole_cards[0], self.hole_cards[1])

        if round_state.round == 'Preflop':
            if to_call == 0:
                if score >= 10:
                    amount = min(max(min_r, self.big_blind * 2), max_r)
                    if amount >= min_r and amount <= max_r:
                        return PokerAction.RAISE, amount
                return PokerAction.CHECK, 0
            else:
                if to_call > remaining_chips:
                    if score >= 12:
                        return PokerAction.ALL_IN, 0
                    return PokerAction.FOLD, 0
                if score >= 8:
                    if score >= 14:
                        raise_by = self.big_blind * 3
                        amount = to_call + raise_by
                        if amount > max_r:
                            return PokerAction.ALL_IN, 0
                        if amount - to_call < min_r:
                            amount = to_call + min_r
                        if amount <= max_r:
                            return PokerAction.RAISE, amount
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
        else:
            best_type, _ = self.get_best_hand(self.hole_cards + round_state.community_cards)
            if best_type >= 4:
                if to_call == 0:
                    amount = int(pot)
                    amount = max(min_r, amount)
                    amount = min(amount, max_r)
                    if amount >= min_r and amount <= max_r:
                        return PokerAction.RAISE, amount
                    return PokerAction.CHECK, 0
                else:
                    if best_type >= 6:
                        raise_by = int(pot)
                        amount = to_call + raise_by
                        if amount > max_r:
                            return PokerAction.ALL_IN, 0
                        if amount - to_call < min_r:
                            amount = to_call + min_r
                        if amount <= max_r:
                            return PokerAction.RAISE, amount
                    return PokerAction.CALL, 0
            elif best_type >= 1:
                if to_call == 0:
                    amount = int(pot / 2)
                    amount = max(min_r, amount)
                    amount = min(amount, max_r)
                    if amount >= min_r and amount <= max_r:
                        return PokerAction.RAISE, amount
                    return PokerAction.CHECK, 0
                else:
                    if to_call < pot / 2:
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0
            else:
                if to_call == 0:
                    return PokerAction.CHECK, 0
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass