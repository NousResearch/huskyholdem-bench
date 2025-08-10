import itertools
from collections import Counter
from typing import List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

# --- Constants for Hand Evaluation ---
RANK_MAP = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
HAND_TYPE_RANK = {
    'HIGH_CARD': 0, 'ONE_PAIR': 1, 'TWO_PAIR': 2, 'THREE_OF_A_KIND': 3,
    'STRAIGHT': 4, 'FLUSH': 5, 'FULL_HOUSE': 6, 'FOUR_OF_A_KIND': 7,
    'STRAIGHT_FLUSH': 8
}

class SimplePlayer(Bot):
    """
    A poker bot that implements a rule-based strategy based on hand strength and position.
    - Fixes the AttributeError from the previous iteration by storing hole cards correctly.
    - Implements a complete hand evaluation system using standard Python libraries.
    - Uses a tiered strategy for pre-flop and post-flop actions to make logical, safe decisions.
    """
    def __init__(self):
        super().__init__()
        self.hole_cards: List[str] = []
        self.all_player_ids: List[int] = []

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        """
        Called at the start of a new hand. This is where the bot receives its private hole cards.
        The primary fix is to store player_hands in an instance variable to be accessed later.
        """
        self.hole_cards = player_hands
        self.all_player_ids = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the start of each betting round (Preflop, Flop, Turn, River). """
        # Currently, no action is needed here. It could be used for logging or complex state updates in the future.
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """
        The main decision-making function. It is called when it's the bot's turn to act.
        """
        # --- Common calculations for any action ---
        my_bet_this_round = round_state.player_bets.get(str(self.id), 0)
        amount_to_call = round_state.current_bet - my_bet_this_round
        can_check = (amount_to_call == 0)

        # --- Dispatch to strategy based on game round ---
        if round_state.round == 'Preflop':
            return self._get_preflop_action(round_state, remaining_chips, can_check, amount_to_call)
        else:
            return self._get_postflop_action(round_state, remaining_chips, can_check, amount_to_call)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of each round. Can be used for opponent modeling. """
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """ Called at the end of the game (e.g., after all hands are played). """
        pass

    # --- Pre-flop Strategy ---

    def _get_preflop_action(self, round_state: RoundStateClient, remaining_chips: int, can_check: bool, amount_to_call: int) -> Tuple[PokerAction, int]:
        strength = self._get_preflop_strength()
        
        # --- Aggressive strategy for premium hands (Top ~10% of hands) ---
        if strength >= 15: # e.g., AA, KK, QQ, AKs, AKo, JJ
            open_raise_amount = int(round_state.min_raise * 3)
            reraise_amount = int(round_state.current_bet * 3 + round_state.pot)
            raise_amount = reraise_amount if round_state.current_bet > 0 else open_raise_amount
            raise_amount = min(raise_amount, remaining_chips)

            if raise_amount >= round_state.min_raise:
                return PokerAction.RAISE, raise_amount
            else: # Cannot make a valid raise, so we must call or go all-in
                if amount_to_call > 0:
                    return PokerAction.ALL_IN if amount_to_call >= remaining_chips else PokerAction.CALL, 0
                return PokerAction.CHECK, 0

        # --- Cautious-aggressive strategy for good hands (Top ~25% of hands) ---
        elif strength >= 10: # e.g., AQs-ATs, KQs-KJs, QJs, JTs, TT-88
            if round_state.current_bet == 0:
                raise_amount = min(int(round_state.min_raise * 2.5), remaining_chips)
                if raise_amount >= round_state.min_raise:
                    return PokerAction.RAISE, raise_amount
            
            if amount_to_call > 0:
                if amount_to_call < remaining_chips * 0.15: # Call if cost is < 15% of stack
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
            return PokerAction.CHECK, 0

        # --- Passive/folding strategy for weak/speculative hands ---
        else:
            if can_check:
                return PokerAction.CHECK, 0
            # Only play if very cheap, e.g., small blind completing in an unraised pot
            if amount_to_call < remaining_chips * 0.05 and round_state.current_bet <= round_state.min_raise * 1.5:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0

    # --- Post-flop Strategy ---

    def _get_postflop_action(self, round_state: RoundStateClient, remaining_chips: int, can_check: bool, amount_to_call: int) -> Tuple[PokerAction, int]:
        hand_rank, _ = self._evaluate_strength(round_state.community_cards)

        # --- Monster Hand (Full House or better) ---
        if hand_rank >= HAND_TYPE_RANK['FULL_HOUSE']:
            raise_amount = min(round_state.pot, round_state.max_raise) # Bet the pot
            if raise_amount >= round_state.min_raise:
                return PokerAction.RAISE, raise_amount
            if amount_to_call > 0:
                return PokerAction.ALL_IN if amount_to_call >= remaining_chips else PokerAction.CALL, 0
            return PokerAction.CHECK, 0

        # --- Very Strong Hand (Two Pair, Trips, Straight, Flush) ---
        elif hand_rank >= HAND_TYPE_RANK['TWO_PAIR']:
            raise_amount = min(int(round_state.pot * 0.7), round_state.max_raise)
            if round_state.current_bet == 0 and raise_amount >= round_state.min_raise:
                return PokerAction.RAISE, raise_amount
            if amount_to_call > 0:
                return PokerAction.CALL, 0
            return PokerAction.CHECK, 0

        # --- Medium Hand (One Pair) ---
        elif hand_rank >= HAND_TYPE_RANK['ONE_PAIR']:
            if can_check:
                bet_amount = min(int(round_state.pot * 0.5), round_state.max_raise)
                if bet_amount >= round_state.min_raise:
                    return PokerAction.RAISE, bet_amount
                return PokerAction.CHECK, 0
            if amount_to_call > 0:
                pot_odds_ratio = amount_to_call / (round_state.pot + amount_to_call + 1e-6)
                if pot_odds_ratio < 0.35 and amount_to_call < remaining_chips * 0.2:
                    return PokerAction.CALL, 0
            return PokerAction.FOLD, 0

        # --- Weak Hand / Draw ---
        else:
            if can_check: return PokerAction.CHECK, 0
            return PokerAction.FOLD, 0

    # --- Hand Evaluation and Scoring Helpers ---

    def _parse_card(self, card_str: str) -> Tuple[int, str]:
        rank = card_str[:-1]
        suit = card_str[-1]
        return RANK_MAP[rank], suit

    def _get_preflop_strength(self) -> int:
        if not self.hole_cards or len(self.hole_cards) != 2: return 0
        c1, c2 = self._parse_card(self.hole_cards[0]), self._parse_card(self.hole_cards[1])
        r1, s1 = c1
        r2, s2 = c2
        if r1 < r2: r1, r2 = r2, r1

        score = {14: 10, 13: 8, 12: 7, 11: 6}.get(r1, r1 / 2.0)
        if r1 == r2: score = max(score * 2, 5)
        if s1 == s2: score += 2
        gap = r1 - r2
        if gap == 1: score += 1
        else: score -= gap
        if (gap < 4 and r1 < 12): score -= 1
        return int(score)

    def _evaluate_strength(self, community_cards: List[str]) -> Tuple[int, List[int]]:
        all_cards = self.hole_cards + community_cards
        if len(all_cards) < 5:
            if len(self.hole_cards) == 2 and self.hole_cards[0][0] == self.hole_cards[1][0]:
                return HAND_TYPE_RANK['ONE_PAIR'], [self._parse_card(self.hole_cards[0])[0]]
            return HAND_TYPE_RANK['HIGH_CARD'], [self._parse_card(c)[0] for c in self.hole_cards]

        parsed_cards = [self._parse_card(c) for c in all_cards]
        best_eval = (-1, [])

        for combo in itertools.combinations(parsed_cards, 5):
            current_eval = self._evaluate_5_card_hand(list(combo))
            if current_eval > best_eval:
                best_eval = current_eval
        return best_eval

    def _evaluate_5_card_hand(self, cards: List[Tuple[int, str]]) -> Tuple[int, List[int]]:
        ranks = sorted([r for r, s in cards], reverse=True)
        suits = {s for r, s in cards}
        rank_counts = Counter(ranks)
        sorted_by_count = sorted(rank_counts.items(), key=lambda i: (i[1], i[0]), reverse=True)
        
        is_flush = len(suits) == 1
        is_straight = len(rank_counts) == 5 and (ranks[0] - ranks[4] == 4 or ranks == [14, 5, 4, 3, 2])
        
        if is_straight and is_flush:
            kicker = [5] if ranks == [14, 5, 4, 3, 2] else [ranks[0]]
            return (HAND_TYPE_RANK['STRAIGHT_FLUSH'], kicker)

        counts = [c for r, c in sorted_by_count]
        kickers = [r for r, c in sorted_by_count]
        
        if counts == [4, 1]: return (HAND_TYPE_RANK['FOUR_OF_A_KIND'], kickers)
        if counts == [3, 2]: return (HAND_TYPE_RANK['FULL_HOUSE'], kickers)
        if is_flush: return (HAND_TYPE_RANK['FLUSH'], ranks)
        if is_straight:
            kicker = [5] if ranks == [14, 5, 4, 3, 2] else [ranks[0]]
            return (HAND_TYPE_RANK['STRAIGHT'], kicker)
        if counts == [3, 1, 1]: return (HAND_TYPE_RANK['THREE_OF_A_KIND'], kickers)
        if counts == [2, 2, 1]: return (HAND_TYPE_RANK['TWO_PAIR'], kickers)
        if counts == [2, 1, 1, 1]: return (HAND_TYPE_RANK['ONE_PAIR'], kickers)
        return (HAND_TYPE_RANK['HIGH_CARD'], ranks)