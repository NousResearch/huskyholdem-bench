import collections
import itertools
from typing import List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    """
    A poker bot that implements a basic tight-aggressive strategy.
    - Pre-flop: Uses a tiered hand-strength system to decide whether to fold, call, or raise.
    - Post-flop: Evaluates hand strength (made hands and draws) to make decisions.
    - Betting: Uses pot-relative bet sizing for value betting and semi-bluffing.
    - Fixes the invalid action bug from the previous iteration by ensuring raise amounts are valid.
    """

    def __init__(self):
        super().__init__()
        self.hole_cards: List[Tuple[int, str]] = []
        self.big_blind_amount: int = 10
        self.all_players: List[int] = []
        self.RANKS = '23456789TJQKA'
        self.SUITS = 'shdc'
        self.rank_map = {rank: i for i, rank in enumerate(self.RANKS, 2)}

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        """ Called once at the start of the simulation. """
        self.big_blind_amount = blind_amount
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the start of each round. """
        # player_hands is a dict mapping player_id (str) to their cards, only ours is visible
        my_cards_str = round_state.player_hands.get(str(self.id))
        if my_cards_str:
            self.hole_cards = self._parse_cards(my_cards_str)
        else:
            self.hole_cards = []

    def _parse_cards(self, cards: List[str]) -> List[Tuple[int, str]]:
        """ e.g. ['Ah', 'Ks'] -> [(14, 'h'), (13, 's')] """
        if not cards:
            return []
        return [(self.rank_map[c[0]], c[1]) for c in cards]

    def _get_preflop_strength(self, hole_cards: List[Tuple[int, str]]) -> int:
        """ Returns a tier score for pre-flop hands, higher is better. """
        if not hole_cards or len(hole_cards) < 2:
            return 0
        card1, card2 = hole_cards[0], hole_cards[1]
        r1, r2 = sorted([card1[0], card2[0]], reverse=True)
        is_suited = (card1[1] == card2[1])
        is_pair = (r1 == r2)

        # Tier 8: AA, KK, QQ, AKs
        if is_pair and r1 >= 12: return 8
        if r1 == 14 and r2 == 13 and is_suited: return 8
        # Tier 7: AKo, AQs, JJ
        if r1 == 14 and r2 == 13: return 7
        if r1 == 14 and r2 == 12 and is_suited: return 7
        if is_pair and r1 == 11: return 7
        # Tier 6: TT, AJs, KQs
        if is_pair and r1 == 10: return 6
        if r1 == 14 and r2 == 11 and is_suited: return 6
        if r1 == 13 and r2 == 12 and is_suited: return 6
        # Tier 5: AQo, 99, ATs
        if r1 == 14 and r2 == 12: return 5
        if is_pair and r1 == 9: return 5
        if r1 == 14 and r2 == 10 and is_suited: return 5
        # Tier 4: AJo, KQo
        if r1 == 14 and r2 == 11: return 4
        if r1 == 13 and r2 == 12: return 4
        # Tier 3: Mid-pairs (77, 88), Suited Connectors, Suited Aces
        if is_pair and r1 in [7, 8]: return 3
        if is_suited and r1 - r2 == 1: return 3
        if is_suited and r1 == 14: return 3
        # Tier 2: Low-pairs, other suited hands
        if is_pair: return 2
        if is_suited: return 2
        # Tier 1: Broadway unsuited
        if r1 >= 10 and r2 >= 10: return 1
        
        return 0

    def _evaluate_5_cards(self, hand: List[Tuple[int, str]]) -> Tuple:
        """ Evaluates a 5-card hand and returns a comparable tuple (rank, high_cards...). """
        ranks = sorted([card[0] for card in hand], reverse=True)
        suits = [card[1] for card in hand]
        is_flush = len(set(suits)) == 1
        is_straight = (len(set(ranks)) == 5 and (max(ranks) - min(ranks) == 4)) or (ranks == [14, 5, 4, 3, 2])
        
        if is_straight and is_flush: return (9, ranks[0] if ranks != [14, 5, 4, 3, 2] else 5)
        
        rank_counts = collections.Counter(ranks)
        counts = sorted(rank_counts.values(), reverse=True)
        main_ranks = sorted(rank_counts.keys(), key=lambda k: (rank_counts[k], k), reverse=True)

        if counts[0] == 4: return (8, main_ranks[0], main_ranks[1])
        if counts == [3, 2]: return (7, main_ranks[0], main_ranks[1])
        if is_flush: return (6, tuple(ranks))
        if is_straight: return (5, ranks[0] if ranks != [14, 5, 4, 3, 2] else 5)
        if counts[0] == 3: return (4, main_ranks[0], main_ranks[1], main_ranks[2])
        if counts == [2, 2, 1]: return (3, main_ranks[0], main_ranks[1], main_ranks[2])
        if counts[0] == 2: return (2, main_ranks[0], tuple(r for r in main_ranks if r != main_ranks[0]))
        return (1, tuple(ranks))

    def _evaluate_7_cards(self, all_7_cards: List[Tuple[int, str]]) -> Tuple[int, Tuple]:
        """ Finds the best 5-card hand from 7 cards. """
        best_hand_score = (0,)
        for hand_5 in itertools.combinations(all_7_cards, 5):
            score = self._evaluate_5_cards(list(hand_5))
            if score > best_hand_score:
                best_hand_score = score
        return best_hand_score[0], best_hand_score[1:]

    def _check_draws(self, all_cards: List[Tuple[int, str]]) -> Tuple[bool, bool]:
        """ Checks for 4-card flush and straight draws. """
        ranks = sorted(list(set([c[0] for c in all_cards])), reverse=True)
        suits = [c[1] for c in all_cards]
        suit_counts = collections.Counter(suits)

        has_flush_draw = max(suit_counts.values()) == 4 if suit_counts else False

        has_straight_draw = False
        if len(ranks) >= 4:
            for i in range(len(ranks) - 3):
                sub_ranks = ranks[i:i+4]
                if max(sub_ranks) - min(sub_ranks) <= 4 and len(set(sub_ranks)) == 4:
                    has_straight_draw = True
                    break
            if {14, 2, 3, 4}.issubset(set(ranks)):
                has_straight_draw = True
        
        return has_flush_draw, has_straight_draw

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """
        my_bet = round_state.player_bets.get(str(self.id), 0)
        amount_to_call = round_state.current_bet - my_bet

        if round_state.round == 'Preflop':
            strength = self._get_preflop_strength(self.hole_cards)
            
            # Action for unraised pots
            if round_state.current_bet <= self.big_blind_amount:
                if strength >= 5: # Strong hands, raise
                    raise_amount = self.big_blind_amount * 3
                elif strength >= 3: # Playable hands, call
                    return (PokerAction.CALL, 0) if amount_to_call > 0 else (PokerAction.CHECK, 0)
                else: # Weak hands, check or fold
                    return (PokerAction.CHECK, 0) if amount_to_call == 0 else (PokerAction.FOLD, 0)
            
            # Action for raised pots
            else:
                if strength >= 7: # Premium hands, re-raise
                    raise_amount = round_state.current_bet * 3
                elif strength >= 5: # Strong hands, call a reasonable raise
                    if amount_to_call < remaining_chips * 0.2:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                else:
                    return (PokerAction.FOLD, 0)

            # Consolidate raise logic, ensuring the action is valid
            safe_raise_amount = max(raise_amount, round_state.min_raise)
            safe_raise_amount = min(safe_raise_amount, round_state.max_raise)
            if safe_raise_amount >= remaining_chips:
                 return (PokerAction.ALL_IN, 0)
            return (PokerAction.RAISE, int(safe_raise_amount))

        else:  # Post-flop (Flop, Turn, River)
            all_cards = self.hole_cards + self._parse_cards(round_state.community_cards)
            hand_rank, _ = self._evaluate_7_cards(all_cards)
            has_flush_draw, has_straight_draw = self._check_draws(all_cards)

            is_strong_hand = hand_rank >= 2 # At least a pair
            is_monster_hand = hand_rank >= 4 # At least trips
            is_good_draw = has_flush_draw or has_straight_draw

            # If we can check
            if amount_to_call == 0:
                if is_strong_hand: # Value bet with a made hand
                    bet_amount = int(round_state.pot * 0.6)
                elif is_good_draw: # Semi-bluff with a good draw
                    bet_amount = int(round_state.pot * 0.4)
                else: # Nothing, check
                    return (PokerAction.CHECK, 0)
                
                # Make sure bet is a valid raise
                safe_bet_amount = max(bet_amount, round_state.min_raise, self.big_blind_amount)
                safe_bet_amount = min(safe_bet_amount, round_state.max_raise)
                if safe_bet_amount >= remaining_chips:
                    return (PokerAction.ALL_IN, 0)
                return (PokerAction.RAISE, int(safe_bet_amount))

            # If facing a bet
            else:
                pot_odds = amount_to_call / (round_state.pot + amount_to_call + 1e-9)
                
                if is_monster_hand: # Raise with a monster hand
                    raise_amount = (round_state.pot + amount_to_call) * 2
                    safe_raise_amount = max(raise_amount, round_state.min_raise)
                    safe_raise_amount = min(safe_raise_amount, round_state.max_raise)
                    if safe_raise_amount >= remaining_chips:
                        return (PokerAction.ALL_IN, 0)
                    return (PokerAction.RAISE, int(safe_raise_amount))

                call_cost_ratio = amount_to_call / (remaining_chips + 1e-9)
                
                # Call with made hands if bet is a reasonable size
                if is_strong_hand and call_cost_ratio < 0.3:
                    return (PokerAction.CALL, 0)

                # Estimate draw equity to decide on calling
                draw_equity_estimate = 0
                if round_state.round == 'Flop':
                    if has_flush_draw: draw_equity_estimate = max(draw_equity_estimate, 0.35)
                    if has_straight_draw: draw_equity_estimate = max(draw_equity_estimate, 0.32)
                elif round_state.round == 'Turn':
                    if has_flush_draw: draw_equity_estimate = max(draw_equity_estimate, 0.19)
                    if has_straight_draw: draw_equity_estimate = max(draw_equity_estimate, 0.17)

                if is_good_draw and pot_odds < draw_equity_estimate:
                    return (PokerAction.CALL, 0)

                return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        self.hole_cards = []

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """ Called at the end of the game. """
        pass