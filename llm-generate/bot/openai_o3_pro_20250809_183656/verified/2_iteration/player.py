import random
from typing import List, Tuple, Dict

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

# try/except in case Treys is not present when this file is imported for linting
try:
    from treys import Card, Evaluator, Deck
except ModuleNotFoundError:  # fallback dummy to avoid hard-crash in environments w/out treys
    Card = None
    Evaluator = None
    Deck = None


class SimplePlayer(Bot):
    """
    A simple yet reasonably strong No-Limit Texas Hold'em bot.
    Main ideas:
        • Pre-flop hand value calculated via “Chen strength” heuristic.
        • Post-flop hand strength estimated by Monte-Carlo simulation (Treys evaluator).
        • Pot-odds aware calling / folding.
        • Value betting / semi-bluffing with strong made hands.
    The implementation purposefully avoids heavy computation and respects
    the 30-second / 100 MB limits.
    """

    # --- Constants / Tunables ------------------------------------------------
    PREFLOP_PREMIUM = 10        # Chen score ≥ 10  :  raise / 3-bet
    PREFLOP_STRONG  = 8         # Chen score ≥ 8   :  open raise / call small raise
    PREFLOP_MEDIUM  = 6         # Chen score ≥ 6   :  limp / call when cheap
    MONTE_CARLO_ITERS = 300     # simulations for post-flop equity estimate
    AGGRESSIVE_STRENGTH = 0.70  # equity threshold to value-bet / raise
    CALL_MARGIN = 0.05          # required edge over pot odds to call

    # ------------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        # Game / round level memory
        self.starting_chips: int = 0
        self.big_blind: int = 0
        self.small_blind: int = 0
        self.hole_cards: List[str] = []
        # Treys evaluator initialised once
        self._evaluator = Evaluator() if Evaluator else None

    # ------------------------------------------------------------------------
    # Callback hooks required by Bot interface
    # ------------------------------------------------------------------------

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
        # competition server passes small blind in blind_amount, big blind is 2×
        self.small_blind = blind_amount
        self.big_blind = blind_amount * 2
        self.hole_cards = player_hands[:] if player_hands else []

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # refresh hole cards if provided in round_state
        self.hole_cards = self._extract_hole_cards(round_state) or self.hole_cards

    # Main decision function --------------------------------------------------
    def get_action(
        self, round_state: RoundStateClient, remaining_chips: int
    ) -> Tuple[PokerAction, int]:

        # Update hole cards just in case
        self.hole_cards = self._extract_hole_cards(round_state) or self.hole_cards
        if not self.hole_cards:
            # Should not happen but fold defensively
            return PokerAction.FOLD, 0

        my_bet = self._my_bet(round_state)
        to_call = max(0, round_state.current_bet - my_bet)
        min_raise = round_state.min_raise
        max_raise = round_state.max_raise

        # Decide based on street ------------------------------------------------
        street = round_state.round.lower()  # 'preflop', 'flop', ...

        if street == "preflop":
            chen = self._chen_strength(self.hole_cards)
            return self._preflop_decision(
                chen, to_call, min_raise, max_raise, remaining_chips
            )

        # Post-flop
        win_prob = self._estimate_equity(self.hole_cards, round_state.community_cards)

        return self._postflop_decision(
            win_prob,
            to_call,
            min_raise,
            max_raise,
            remaining_chips,
            round_state.pot,
        )

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Nothing to reset except hole cards
        self.hole_cards = []

    def on_end_game(
        self,
        round_state: RoundStateClient,
        player_score: float,
        all_scores: dict,
        active_players_hands: dict,
    ):
        # No persistent state needed between games
        pass

    # ------------------------------------------------------------------------
    # Strategy helpers
    # ------------------------------------------------------------------------

    def _preflop_decision(
        self,
        chen: float,
        to_call: int,
        min_raise: int,
        max_raise: int,
        remaining_chips: int,
    ) -> Tuple[PokerAction, int]:
        """
        Simple Chen-formula based pre-flop logic.
        """
        # When open action (no bet to call)
        if to_call == 0:
            if chen >= self.PREFLOP_PREMIUM:
                # Open big
                raise_amt = max(min_raise, int(self.big_blind * 4))
                raise_amt = min(raise_amt, max_raise, remaining_chips)
                if raise_amt >= min_raise:
                    return PokerAction.RAISE, raise_amt
            elif chen >= self.PREFLOP_STRONG:
                raise_amt = max(min_raise, int(self.big_blind * 3))
                raise_amt = min(raise_amt, max_raise, remaining_chips)
                if raise_amt >= min_raise:
                    return PokerAction.RAISE, raise_amt
            elif chen >= self.PREFLOP_MEDIUM:
                return PokerAction.CHECK, 0
            else:
                return PokerAction.CHECK, 0

        # Facing a bet ---------------------------------------------------------
        else:
            # All-in short stacks
            if remaining_chips <= to_call:
                return PokerAction.ALL_IN, 0

            if chen >= self.PREFLOP_PREMIUM:
                # Occasionally 3-bet for value
                raise_amt = max(min_raise, to_call * 3)
                raise_amt = min(raise_amt, max_raise, remaining_chips)
                if raise_amt >= min_raise:
                    return PokerAction.RAISE, raise_amt
                return PokerAction.CALL, 0
            elif chen >= self.PREFLOP_STRONG:
                # Call small bets, otherwise fold
                if to_call <= self.big_blind * 4:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
            elif chen >= self.PREFLOP_MEDIUM:
                # Call min raises only
                if to_call <= self.big_blind * 2:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
            else:
                return PokerAction.FOLD, 0

    # -------------------------------------------------------------------

    def _postflop_decision(
        self,
        win_prob: float,
        to_call: int,
        min_raise: int,
        max_raise: int,
        remaining_chips: int,
        pot: int,
    ) -> Tuple[PokerAction, int]:
        """
        Post-flop decision using equity vs pot-odds.
        """
        if to_call == 0:
            # We are not facing a bet.
            if win_prob >= self.AGGRESSIVE_STRENGTH:
                # Value bet half-pot
                raise_amt = max(
                    min_raise, min(max_raise, int(max(self.small_blind, pot / 2)))
                )
                if raise_amt >= min_raise and raise_amt <= remaining_chips:
                    return PokerAction.RAISE, raise_amt
            return PokerAction.CHECK, 0

        # We are facing a bet --------------------------------------------------
        # Pot odds threshold to call
        pot_odds = to_call / max(pot + to_call, 1)
        if win_prob > pot_odds + self.CALL_MARGIN:
            # Possibly re-raise with very strong hand
            if win_prob >= self.AGGRESSIVE_STRENGTH and remaining_chips > to_call + min_raise:
                raise_amt = max(min_raise, int(pot))  # pot-sized raise
                raise_amt = min(raise_amt, max_raise, remaining_chips - to_call)
                if raise_amt >= min_raise:
                    return PokerAction.RAISE, raise_amt
            return PokerAction.CALL, 0

        # Fold when equity insufficient
        return PokerAction.FOLD, 0

    # ------------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _rank_value(rank_char: str) -> int:
        return "23456789TJQKA".index(rank_char)

    def _chen_strength(self, cards: List[str]) -> float:
        """
        Compute the ‘Chen formula’ rating for a two-card starting hand.
        """
        if len(cards) != 2:
            return 0.0
        r1, s1 = cards[0][0], cards[0][1]
        r2, s2 = cards[1][0], cards[1][1]
        value_map = {
            "A": 10,
            "K": 8,
            "Q": 7,
            "J": 6,
            "T": 5,
            "9": 4.5,
            "8": 4,
            "7": 3.5,
            "6": 3,
            "5": 2.5,
            "4": 2,
            "3": 1.5,
            "2": 1,
        }

        high = max(value_map[r1], value_map[r2])
        low = min(value_map[r1], value_map[r2])
        points = high

        # Pair
        if r1 == r2:
            points = max(5, points * 2)

        # Suited
        if s1 == s2:
            points += 2

        # Gap
        gap = abs(self._rank_value(r1) - self._rank_value(r2)) - 1
        if gap == 1:
            points -= 1
        elif gap == 2:
            points -= 2
        elif gap == 3:
            points -= 4
        elif gap >= 4:
            points -= 5

        # Straight bonus
        if gap <= 1 and (self._rank_value(r1) <= self._rank_value("9") and self._rank_value(r2) <= self._rank_value("9")):
            points += 1

        return max(points, 0)

    # --------------------------------------------------------------------

    def _estimate_equity(
        self, hole_cards: List[str], community_cards: List[str]
    ) -> float:
        """
        Monte-Carlo estimate of win probability versus one random opponent.
        Uses the Treys library for hand evaluation.
        """
        if not self._evaluator or not hole_cards:
            return 0.5  # fallback neutral

        # fast path: showdown (5 community cards) – evaluate directly
        if len(community_cards) == 5:
            deck_cards = []  # no draws needed
            opp_hand = [None, None]  # placeholder
            my_score = self._evaluator.evaluate(
                [Card.new(c) for c in hole_cards],
                [Card.new(c) for c in community_cards],
            )
            # Enumerate all possible opponent hands (too many) – instead approximate
            # treat win_prob as inverse proportional to hand rank
            return max(0.01, 1 - my_score / 7462)  # 7462 distinct ranks

        # Monte-Carlo simulation
        wins = 0
        ties = 0
        iterations = self.MONTE_CARLO_ITERS
        # Build deck minus known cards
        known = set(hole_cards + community_cards)
        deck = [
            c
            for c in [
                r + s
                for r in "23456789TJQKA"
                for s in "shdc"
            ]
            if c not in known
        ]
        deck_len = len(deck)

        my_cards_treys = [Card.new(c) for c in hole_cards]
        community_treys = [Card.new(c) for c in community_cards]

        for _ in range(iterations):
            # Randomly pick rest of board + opponent hand
            random.shuffle(deck)
            need_board = 5 - len(community_cards)
            board_sample = deck[:need_board]
            opp_hand_sample = deck[need_board : need_board + 2]

            opp_cards_treys = [Card.new(c) for c in opp_hand_sample]
            board_treys = community_treys + [Card.new(c) for c in board_sample]

            my_score = self._evaluator.evaluate(my_cards_treys, board_treys)
            opp_score = self._evaluator.evaluate(opp_cards_treys, board_treys)

            if my_score < opp_score:
                wins += 1
            elif my_score == opp_score:
                ties += 1

        return (wins + ties * 0.5) / iterations if iterations else 0.5

    # --------------------------------------------------------------------

    def _my_bet(self, round_state: RoundStateClient) -> int:
        return round_state.player_bets.get(str(self.id), 0)

    @staticmethod
    def _extract_hole_cards(round_state: RoundStateClient) -> List[str]:
        """
        Attempt to retrieve our current hole cards from the round_state if field present.
        """
        if hasattr(round_state, "player_hands") and round_state.player_hands:
            # keys likely str IDs
            return round_state.player_hands.get(str(getattr(round_state, "player_id", "")), [])
        return []