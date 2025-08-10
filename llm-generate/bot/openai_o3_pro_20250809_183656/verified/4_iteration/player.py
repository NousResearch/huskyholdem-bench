from typing import List, Tuple, Dict
from collections import Counter

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


RANK_ORDER = "23456789TJQKA"
RANK_VALUE: Dict[str, int] = {r: i for i, r in enumerate(RANK_ORDER, 2)}


class SimplePlayer(Bot):
    """
    A very small-footprint, safety-first poker bot.

    Goals for this iteration:
      1. NEVER return an illegal action (fixed Iter-3 bug that raised 0).
      2. Play tight-aggressive pre-flop; simple strength heuristics post-flop.
      3. Remain within all memory / time budgets (pure Python, no heavy libs).
    """

    def __init__(self):
        super().__init__()
        # game-level information
        self.starting_chips: int = 0
        self.blind_amount: int = 0               # small blind size
        self.hole_cards: List[str] = []          # this bot’s two cards (e.g. ['Ah', 'Kd'])
        self.players: List[int] = []             # ids of all players at table

        # round-level information
        self.round_num: int = 0
        self.remaining_chips: int = 0

    # -------------------------------------------------------------
    # Helper functions
    # -------------------------------------------------------------
    @staticmethod
    def card_rank(card: str) -> str:
        """Return rank character of a card (e.g. 'A' for 'Ah')."""
        return card[0]

    @staticmethod
    def card_suit(card: str) -> str:
        """Return suit character of a card (e.g. 'h' for 'Ah')."""
        return card[1]

    @staticmethod
    def is_suited(card1: str, card2: str) -> bool:
        return SimplePlayer.card_suit(card1) == SimplePlayer.card_suit(card2)

    @staticmethod
    def chen_formula(card1: str, card2: str) -> float:
        """
        Very light implementation of the Chen formula for starting-hand strength.
        Good enough for tight-aggressive decisions while staying trivial to compute.
        """
        ranks = [SimplePlayer.card_rank(card1), SimplePlayer.card_rank(card2)]
        values = sorted([RANK_VALUE[r] for r in ranks], reverse=True)
        high = values[0]
        low = values[1]

        # base score from the highest card
        if high >= 14:              # Ace
            score = 10
        elif high == 13:            # King
            score = 8
        elif high == 12:            # Queen
            score = 7
        elif high == 11:            # Jack
            score = 6
        else:                       # 2-10
            score = high / 2.0

        # Pair bonus
        if ranks[0] == ranks[1]:
            score = max(5, high * 2)
            if high < 12:           # smaller than Queen
                score += 1
        # suited bonus
        if SimplePlayer.is_suited(card1, card2):
            score += 2

        # gap penalty
        gap = abs(high - low) - 1
        if gap == 1:
            score -= 1
        elif gap == 2:
            score -= 2
        elif gap == 3:
            score -= 4
        elif gap >= 4:
            score -= 5

        # Compensation for small gap & both cards >= Ten
        if gap <= 1 and high < 12 and low >= 10:
            score += 1

        return max(score, 0)

    def preflop_strength(self) -> float:
        """Return Chen strength of current hole cards (0-20 scale)."""
        if len(self.hole_cards) != 2:
            return 0.0
        return self.chen_formula(self.hole_cards[0], self.hole_cards[1])

    @staticmethod
    def hand_rank_category(all_cards: List[str]) -> int:
        """
        Extremely lean evaluator that only cares about category, not kickers.
        Returns an integer representing hand strength category:
            7 = Straight/Flush or better
            6 = Four of a kind
            5 = Full house
            4 = Flush
            3 = Straight
            2 = Three of a kind
            1 = Two pair / One pair
            0 = High card
        NOTE: This heuristic lumps several categories together but is adequate
        for fold/continue decisions.
        """
        ranks = [SimplePlayer.card_rank(c) for c in all_cards]
        suits = [SimplePlayer.card_suit(c) for c in all_cards]
        rank_counts = Counter(ranks).values()
        flush = max(Counter(suits).values(), default=0) >= 5

        # Straight detection
        rank_set = {RANK_VALUE[r] for r in ranks}
        # Handle wheel straight (A-5)
        if {14, 5, 4, 3, 2}.issubset(rank_set):
            straight = True
        else:
            straight = any(
                all(v + offset in rank_set for offset in range(5))
                for v in range(10, 1, -1)
            )

        if flush and straight:
            return 7
        if 4 in rank_counts:
            return 6
        if 3 in rank_counts and 2 in rank_counts:
            return 5
        if flush:
            return 4
        if straight:
            return 3
        if 3 in rank_counts:
            return 2
        if list(rank_counts).count(2) >= 1:
            return 1
        return 0

    # -------------------------------------------------------------
    # Bot interface methods
    # -------------------------------------------------------------
    def on_start(
        self,
        starting_chips: int,
        player_hands: List[str],
        blind_amount: int,
        big_blind_player_id: int,
        small_blind_player_id: int,
        all_players: List[int],
    ):
        self.starting_chips = starting_chips
        self.remaining_chips = starting_chips
        self.blind_amount = blind_amount
        self.players = all_players
        # According to server spec, player_hands is this player's two cards
        self.hole_cards = player_hands if len(player_hands) == 2 else []

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.round_num = round_state.round_num
        self.remaining_chips = remaining_chips

    # -------------------------------------------------------------
    # Main decision logic
    # -------------------------------------------------------------
    def get_action(
        self, round_state: RoundStateClient, remaining_chips: int
    ) -> Tuple[PokerAction, int]:
        """
        Decide action using very simple but safe logic.
        """
        try:
            # Basic round information
            pot = round_state.pot
            community = round_state.community_cards
            to_call = max(
                0,
                round_state.current_bet
                - round_state.player_bets.get(str(self.id), 0),
            )

            # If we are already all-in, nothing to do
            if remaining_chips <= 0:
                return PokerAction.CALL, 0

            # -------------------------------------------------
            # Determine desired intent (fold / check / call / raise)
            # -------------------------------------------------
            intent_action: PokerAction
            raise_amount: int = 0

            # ------------- PREFLOP --------------------------
            if len(community) == 0:
                strength = self.preflop_strength()

                # Aggressive with premium hands
                if strength >= 10:  # Chen score for ~top 10% hands
                    if to_call == 0:
                        intent_action = PokerAction.RAISE
                    elif to_call <= 3 * self.blind_amount:
                        intent_action = PokerAction.RAISE
                    else:
                        intent_action = PokerAction.CALL
                elif strength >= 7:  # playable but not premium
                    if to_call == 0:
                        intent_action = PokerAction.CHECK
                    elif to_call <= 2 * self.blind_amount:
                        intent_action = PokerAction.CALL
                    else:
                        intent_action = PokerAction.FOLD
                else:
                    # Weak hand
                    intent_action = PokerAction.CHECK if to_call == 0 else PokerAction.FOLD
            # ------------- POSTFLOP --------------------------
            else:
                category = self.hand_rank_category(self.hole_cards + community)

                # Very strong made hand
                if category >= 4:  # Flush / Straight or better
                    if to_call == 0:
                        intent_action = PokerAction.RAISE
                    else:
                        # trap sometimes by calling small bets
                        intent_action = PokerAction.CALL if to_call < pot / 4 else PokerAction.RAISE
                # Medium strength (pair / trips etc.)
                elif category >= 1:
                    if to_call == 0:
                        intent_action = PokerAction.CHECK
                    elif to_call <= pot / 10:
                        intent_action = PokerAction.CALL
                    else:
                        intent_action = PokerAction.FOLD
                else:
                    # No made hand – fold to any bet
                    intent_action = PokerAction.CHECK if to_call == 0 else PokerAction.FOLD

            # -------------------------------------------------
            # Translate intent into legal action
            # -------------------------------------------------
            if intent_action == PokerAction.CHECK:
                if to_call == 0:
                    return PokerAction.CHECK, 0
                # fall back to CALL/FOLD safety
                intent_action = PokerAction.CALL

            if intent_action == PokerAction.FOLD:
                if to_call == 0:
                    return PokerAction.CHECK, 0  # free option available
                return PokerAction.FOLD, 0

            if intent_action == PokerAction.CALL:
                if to_call == 0:
                    return PokerAction.CHECK, 0
                if to_call >= remaining_chips:
                    return PokerAction.ALL_IN, 0
                return PokerAction.CALL, 0

            # RAISE / ALL-IN path
            min_raise = round_state.min_raise
            max_raise = round_state.max_raise

            if max_raise <= 0 or min_raise is None:
                # Cannot legally raise – fallback
                if to_call == 0:
                    return PokerAction.CHECK, 0
                if to_call >= remaining_chips:
                    return PokerAction.ALL_IN, 0
                return PokerAction.CALL, 0

            # Simple sizing: 3× to_call or minimum raise if first in
            raise_amount = max(min_raise, to_call * 2 if to_call else self.blind_amount * 3)
            raise_amount = min(raise_amount, max_raise)

            # Ensure raise actually exceeds current by required min
            if raise_amount < min_raise or raise_amount <= 0:
                # Fallback safety
                if to_call == 0:
                    return PokerAction.CHECK, 0
                if to_call >= remaining_chips:
                    return PokerAction.ALL_IN, 0
                return PokerAction.CALL, 0

            # If raise would commit nearly all chips, just go all-in
            if raise_amount >= remaining_chips:
                return PokerAction.ALL_IN, 0

            return PokerAction.RAISE, raise_amount

        except Exception:
            # Any unexpected problem – be safe
            if (
                round_state.current_bet
                - round_state.player_bets.get(str(self.id), 0)
                == 0
            ):
                return PokerAction.CHECK, 0
            return PokerAction.FOLD, 0

    # -------------------------------------------------------------
    # Callbacks (no internal state needed for now)
    # -------------------------------------------------------------
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        self.remaining_chips = remaining_chips

    def on_end_game(
        self,
        round_state: RoundStateClient,
        player_score: float,
        all_scores: dict,
        active_players_hands: dict,
    ):
        # Reset long-lived state if needed
        self.hole_cards = []
        self.remaining_chips = self.starting_chips