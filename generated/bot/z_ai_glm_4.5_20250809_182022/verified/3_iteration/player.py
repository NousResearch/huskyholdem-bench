from typing import List, Tuple, Dict, Any
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import itertools
from collections import Counter

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.big_blind = 0
        self.hole_cards = []
        self.precomputed_strength = {}

    def set_id(self, player_id: int) -> None:
        super().set_id(player_id)

    def _get_card_rank(self, card: str) -> int:
        rank_char = card[0]
        if rank_char == 'A':
            return 14
        elif rank_char == 'K':
            return 13
        elif rank_char == 'Q':
            return 12
        elif rank_char == 'J':
            return 11
        elif rank_char == 'T':
            return 10
        else:
            return int(rank_char)

    def _get_card_suit(self, card: str) -> str:
        return card[1]

    def _evaluate_5_cards(self, cards: List[str]) -> Tuple[int, List[int]]:
        ranks = sorted([self._get_card_rank(card) for card in cards], reverse=True)
        suits = [self._get_card_suit(card) for card in cards]
        
        is_flush = len(set(suits)) == 1
        unique_ranks = sorted(set(ranks))
        is_straight = False
        high_straight = 0
        
        if len(unique_ranks) == 5:
            if unique_ranks[-1] - unique_ranks[0] == 4:
                is_straight = True
                high_straight = unique_ranks[-1]
            elif set(unique_ranks) == {14, 2, 3, 4, 5}:
                is_straight = True
                high_straight = 5
        
        if is_straight and is_flush:
            return (9, [high_straight])
        
        count_rank = Counter(ranks)
        count_rank_val = sorted(count_rank.values(), reverse=True)
        
        if count_rank_val[0] == 4:
            quad_rank = [rank for rank, count in count_rank.items() if count == 4][0]
            kicker = [rank for rank, count in count_rank.items() if count == 1][0]
            return (8, [quad_rank, kicker])
        
        if count_rank_val[0] == 3 and count_rank_val[1] == 2:
            triple_rank = [rank for rank, count in count_rank.items() if count == 3][0]
            pair_rank = [rank for rank, count in count_rank.items() if count == 2][0]
            return (7, [triple_rank, pair_rank])
        
        if is_flush:
            return (6, sorted(ranks, reverse=True))
        
        if is_straight:
            return (5, [high_straight])
        
        if count_rank_val[0] == 3:
            triple_rank = [rank for rank, count in count_rank.items() if count == 3][0]
            kickers = sorted([rank for rank, count in count_rank.items() if count == 1], reverse=True)
            return (4, [triple_rank] + kickers)
        
        if count_rank_val[0] == 2 and count_rank_val[1] == 2:
            pairs = sorted([rank for rank, count in count_rank.items() if count == 2], reverse=True)
            kicker = [rank for rank, count in count_rank.items() if count == 1][0]
            return (3, pairs + [kicker])
        
        if count_rank_val[0] == 2:
            pair_rank = [rank for rank, count in count_rank.items() if count == 2][0]
            kickers = sorted([rank for rank, count in count_rank.items() if count == 1], reverse=True)
            return (2, [pair_rank] + kickers)
        
        return (1, sorted(ranks, reverse=True))

    def _evaluate_hand(self, hole_cards: List[str], community_cards: List[str]) -> Tuple[int, List[int]]:
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            return (1, [self._get_card_rank(card) for card in all_cards][:5])
        
        best_rank = 0
        best_highs = []
        for combo in itertools.combinations(all_cards, 5):
            rank, highs = self._evaluate_5_cards(list(combo))
            if rank > best_rank or (rank == best_rank and highs > best_highs):
                best_rank = rank
                best_highs = highs
        return (best_rank, best_highs)

    def _preflop_strength(self, hole_cards: List[str]) -> int:
        if len(hole_cards) != 2:
            return 0
            
        ranks = sorted([self._get_card_rank(card) for card in hole_cards], reverse=True)
        suits = [self._get_card_suit(card) for card in hole_cards]
        
        if ranks[0] == ranks[1]:
            return ranks[0] * 2 + 20
        
        gap = ranks[0] - ranks[1] - 1
        base = ranks[0] + ranks[1]
        if suits[0] == suits[1]:
            base += 5
        
        if gap == 0:
            base += 7
        elif gap == 1:
            base += 5
        elif gap == 2:
            base += 3
        elif gap == 3:
            base += 1
        else:
            base -= (gap - 3) * 2
        
        return base

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.big_blind = blind_amount
        index = all_players.index(self.id)
        hand_str = player_hands[index]
        
        if len(hand_str) == 4:
            self.hole_cards = [hand_str[0:2], hand_str[2:4]]
        else:
            self.hole_cards = hand_str.split()
            if len(self.hole_cards) == 1 and len(hand_str) >= 4:
                s = self.hole_cards[0]
                self.hole_cards = [s[0:2], s[2:4]]

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            hole_cards = self.hole_cards
            community_cards = round_state.community_cards
            current_round = round_state.round
            current_bet = round_state.current_bet
            min_raise = round_state.min_raise
            max_raise = round_state.max_raise
            pot = round_state.pot
            
            our_id_str = str(self.id)
            our_bet = round_state.player_bets.get(our_id_str, 0)
            call_amount = current_bet - our_bet
            
            if current_round == 'Preflop':
                strength = self._preflop_strength(hole_cards)
            else:
                rank, _ = self._evaluate_hand(hole_cards, community_cards)
                strength = rank
            
            if call_amount == 0:
                if strength >= 80 or (current_round != 'Preflop' and strength >= 6):
                    raise_amount = min(3 * pot, max_raise)
                    if raise_amount < min_raise:
                        if min_raise <= max_raise:
                            raise_amount = min_raise
                        else:
                            return (PokerAction.ALL_IN, 0)
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                if current_round == 'Preflop':
                    if strength >= 80:
                        raise_amount = min(3 * pot, max_raise)
                        if raise_amount < min_raise:
                            if min_raise <= max_raise:
                                raise_amount = min_raise
                            else:
                                return (PokerAction.ALL_IN, 0)
                        return (PokerAction.RAISE, raise_amount)
                    elif strength >= 50:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                else:
                    if strength >= 6:
                        raise_amount = min(2 * pot, max_raise)
                        if raise_amount < min_raise:
                            if min_raise <= max_raise:
                                return (PokerAction.RAISE, min_raise)
                            else:
                                return (PokerAction.ALL_IN, 0)
                        return (PokerAction.RAISE, raise_amount)
                    elif strength >= 3:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
        except Exception:
            return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass