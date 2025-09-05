import random
from itertools import combinations
from collections import Counter
from typing import List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    """
    A poker bot for No-Limit Texas Hold'em.
    
    Strategy:
    - Pre-flop: Uses a hand-ranking system based on Sklansky-Karlson groups to decide whether to fold, call, or raise.
    - Post-flop: Evaluates the best 5-card hand from the 7 available cards (2 hole + 5 community).
    - Betting:
        - Bets aggressively with very strong hands (e.g., set or better).
        - Plays more cautiously with medium-strength hands (e.g., top pair), preferring to check or call.
        - Folds weak hands unless checking is a free option.
    - Bet Sizing: Raises are sized relative to the pot.
    - Validation: All actions are validated to be within legal amounts to prevent forced folds from errors.
    """
    def __init__(self):
        super().__init__()
        self.all_my_hands: List[str] = []
        self.hole_cards: List[str] = []
        self.big_blind_amount: int = 0
        self.num_players: int = 0
        
        self.CARD_RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        self.HAND_STRENGTH = {
            'HIGH_CARD': 0, 'ONE_PAIR': 1, 'TWO_PAIR': 2, 'THREE_OF_A_KIND': 3,
            'STRAIGHT': 4, 'FLUSH': 5, 'FULL_HOUSE': 6, 'FOUR_OF_A_KIND': 7,
            'STRAIGHT_FLUSH': 8, 'ROYAL_FLUSH': 9,
        }

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        """ Called once at the start of the game. """
        self.all_my_hands = player_hands
        self.big_blind_amount = blind_amount
        self.num_players = len(all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the start of each hand. """
        round_index = round_state.round_num
        if round_index < len(self.all_my_hands):
            self.hole_cards = self.all_my_hands[round_index]
        else:
            self.hole_cards = [] 

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Main logic for deciding an action. """
        my_bet = round_state.player_bets.get(str(self.id), 0)
        amount_to_call = round_state.current_bet - my_bet
        can_check = (amount_to_call == 0)

        if not self.hole_cards:
            return PokerAction.FOLD, 0
            
        if round_state.round == 'Preflop':
            return self._get_preflop_action(round_state, remaining_chips, amount_to_call, can_check)
        else:
            return self._get_postflop_action(round_state, remaining_chips, amount_to_call, can_check)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of a hand. Can be used for opponent modeling. """
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """ Called at the end of the game session. """
        pass

    def _parse_card(self, card_str: str) -> Tuple[int, str]:
        """
        Parses a card string like 'Kh' into (rank, suit).
        This fixes the ValueError from the previous iteration.
        """
        if not card_str or len(card_str) < 2:
            return (0, '')
        rank_str = card_str[:-1]
        suit = card_str[-1]
        rank = self.CARD_RANKS.get(rank_str, 0)
        return (rank, suit)

    def _get_preflop_strength(self) -> int:
        """ Calculates pre-flop hand strength on a scale of 1 (premium) to 5 (fold). """
        if not self.hole_cards or len(self.hole_cards) != 2:
            return 5
            
        c1_str, c2_str = self.hole_cards
        r1, s1 = self._parse_card(c1_str)
        r2, s2 = self._parse_card(c2_str)
        
        suited = (s1 == s2)
        if r1 < r2:
            r1, r2 = r2, r1

        if r1 == r2:
            if r1 >= 11: return 1
            if r1 >= 7: return 2
            return 3
        
        if suited:
            if r1 == 14 and r2 >= 10: return 1
            if r1 >= 11 and r2 >= 10: return 2
            if r1 == 14: return 3
            if (r1 - r2) == 1: return 3
            return 4
        else:
            if (r1 == 14 and r2 >= 12) or (r1 == 13 and r2 == 12): return 2
            if r1 == 14 and r2 == 11: return 3
            if r1 == 13 and r2 == 11 or r1 == 12 and r2 == 11: return 3
            if r1 >= 10 and (r1 - r2) == 1: return 4
            return 5

    def _evaluate_hand(self, five_cards: List[Tuple[int, str]]) -> Tuple[int, tuple]:
        """ Evaluates a 5-card hand and returns its rank and tie-breaking ranks. """
        ranks = sorted([c[0] for c in five_cards], reverse=True)
        suits = [c[1] for c in five_cards]

        is_flush = len(set(suits)) == 1
        is_straight = (max(ranks) - min(ranks) == 4 and len(set(ranks)) == 5) or (ranks == [14, 5, 4, 3, 2])
        
        if is_straight and is_flush:
            if ranks == [14, 13, 12, 11, 10]: return (self.HAND_STRENGTH['ROYAL_FLUSH'], tuple(ranks))
            if ranks == [14, 5, 4, 3, 2]: return (self.HAND_STRENGTH['STRAIGHT_FLUSH'], (5,4,3,2,1))
            return (self.HAND_STRENGTH['STRAIGHT_FLUSH'], tuple(ranks))

        rank_counts = Counter(ranks)
        vals_by_count = sorted(rank_counts.items(), key=lambda x: (-x[1], -x[0]))
        
        counts = [v[1] for v in vals_by_count]
        major_ranks = tuple([v[0] for v in vals_by_count])

        if counts == [4, 1]: return (self.HAND_STRENGTH['FOUR_OF_A_KIND'], major_ranks)
        if counts == [3, 2]: return (self.HAND_STRENGTH['FULL_HOUSE'], major_ranks)
        if is_flush: return (self.HAND_STRENGTH['FLUSH'], tuple(ranks))
        if is_straight:
            if ranks == [14, 5, 4, 3, 2]: return (self.HAND_STRENGTH['STRAIGHT'], (5,4,3,2,1))
            return (self.HAND_STRENGTH['STRAIGHT'], tuple(ranks))
        if counts[0] == 3: return (self.HAND_STRENGTH['THREE_OF_A_KIND'], major_ranks)
        if counts[:2] == [2, 2]: return (self.HAND_STRENGTH['TWO_PAIR'], major_ranks)
        if counts[0] == 2: return (self.HAND_STRENGTH['ONE_PAIR'], major_ranks)

        return (self.HAND_STRENGTH['HIGH_CARD'], tuple(ranks))

    def _evaluate_7_cards(self, hole_cards: List[str], community_cards: List[str]) -> Tuple[int, tuple]:
        """ Finds the best 5-card hand from 7 cards. """
        all_cards_str = hole_cards + community_cards
        if len(all_cards_str) < 5:
            parsed_hole = sorted([self._parse_card(c)[0] for c in hole_cards], reverse=True)
            return (self.HAND_STRENGTH['HIGH_CARD'], tuple(parsed_hole))
            
        all_cards = [self._parse_card(c) for c in all_cards_str]
        
        best_hand_eval = (-1, ())
        for combo in combinations(all_cards, 5):
            current_eval = self._evaluate_hand(list(combo))
            if current_eval > best_hand_eval:
                best_hand_eval = current_eval
                
        return best_hand_eval

    def _get_preflop_action(self, round_state, remaining_chips, amount_to_call, can_check):
        strength = self._get_preflop_strength()
        num_raises = sum(1 for action in round_state.player_actions.values() if 'Raise' in action or 'All' in action)

        if strength == 1:
            raise_amount = self.big_blind_amount * 4 if num_raises == 0 else round_state.pot * 2 + round_state.current_bet
            return self._validate_action(PokerAction.RAISE, raise_amount, round_state, remaining_chips)

        if strength == 2:
            if num_raises == 0:
                return self._validate_action(PokerAction.RAISE, self.big_blind_amount * 3, round_state, remaining_chips)
            elif num_raises < 2 and amount_to_call < remaining_chips * 0.15:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        if strength == 3:
            if num_raises == 0:
                return PokerAction.CALL if not can_check else PokerAction.CHECK, 0
            if amount_to_call <= self.big_blind_amount * 2:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        return PokerAction.CHECK if can_check else PokerAction.FOLD, 0

    def _get_postflop_action(self, round_state, remaining_chips, amount_to_call, can_check):
        hand_rank, _ = self._evaluate_7_cards(self.hole_cards, round_state.community_cards)
        pot = round_state.pot

        if hand_rank >= self.HAND_STRENGTH['FULL_HOUSE']:
            bet_amount = pot * 1.2
            return self._validate_action(PokerAction.RAISE, bet_amount, round_state, remaining_chips)
        
        if hand_rank >= self.HAND_STRENGTH['TWO_PAIR']:
            bet_amount = int(pot * 0.7)
            if can_check:
                return self._validate_action(PokerAction.RAISE, bet_amount, round_state, remaining_chips)
            else:
                return PokerAction.CALL, 0
        
        if hand_rank >= self.HAND_STRENGTH['ONE_PAIR']:
            if can_check:
                return PokerAction.CHECK, 0
            else:
                pot_odds = amount_to_call / (pot + amount_to_call + 1e-9)
                if pot_odds < 0.3:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
        
        return PokerAction.CHECK if can_check else PokerAction.FOLD, 0

    def _validate_action(self, action: PokerAction, amount: int, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        if action != PokerAction.RAISE:
            return action, 0

        amount = int(amount)
        my_current_bet = round_state.player_bets.get(str(self.id), 0)
        
        if amount >= remaining_chips + my_current_bet:
            return PokerAction.ALL_IN, 0
        
        # Ensure raise is at least the minimum allowed total bet size
        if amount < round_state.min_raise:
            amount = round_state.min_raise

        # Ensure we don't bet more than we have
        if amount > remaining_chips + my_current_bet:
            amount = remaining_chips + my_current_bet

        if amount >= remaining_chips + my_current_bet:
            return PokerAction.ALL_IN, 0

        return PokerAction.RAISE, amount