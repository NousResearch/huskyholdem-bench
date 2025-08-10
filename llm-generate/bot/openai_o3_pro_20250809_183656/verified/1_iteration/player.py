import random
from typing import List, Tuple, Dict

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

# Optional fast hand-strength evaluator
try:
    from treys import Evaluator, Card, Deck
    _HAVE_TREYS = True
except ImportError:  # Fallback to a simple heuristic evaluator
    _HAVE_TREYS = False


class SimplePlayer(Bot):
    """
    A very compact yet surprisingly strong No-Limit Texas Hold’em bot.
    Core ideas:
      • Pre-flop: fixed hand-strength chart with position awareness.
      • Post-flop: Hand-strength (equity) Monte-Carlo estimate (fast with
        treys, heuristic fallback otherwise) turned into an aggression
        factor.
      • Always double-checks action legality before sending it to the
        engine in order to avoid auto-folds.
    """

    # ----- CONFIGURABLE CONSTANTS -----
    PREFLOP_PREMIUM = {
        "AA", "KK", "QQ", "JJ", "AKs"
    }
    PREFLOP_STRONG = {
        "TT", "99", "88", "AQs", "AJs", "AK",
        "KQs", "77", "66"
    }
    MONTE_CARLO_ITERS = 75          # Equity simulations per decision
    AGGRO_THRESHOLD = 0.70          # Equity for strong aggression
    CALL_THRESHOLD = 0.45           # Minimum equity to continue
    RAISE_FACTOR = 2.5              # Pot-sized raise factor
    MIN_STACK_FOR_ALLIN = 0.4       # Push if stack/pot < this fraction
    RANDOM_SEED = 7                 # Fixed seed for reproducibility
    # ----------------------------------

    def __init__(self):
        super().__init__()
        random.seed(self.RANDOM_SEED)
        self.evaluator = Evaluator() if _HAVE_TREYS else None
        self.starting_stack = 0
        self.big_blind = 0
        self.hole_cards: List[str] = []

    # ------------------------------------------------------------------ #
    #  ENGINE CALLBACKS
    # ------------------------------------------------------------------ #
    def on_start(
        self,
        starting_chips: int,
        player_hands: List[str],
        blind_amount: int,
        big_blind_player_id: int,
        small_blind_player_id: int,
        all_players: List[int],
    ):
        self.starting_stack = starting_chips
        self.big_blind = blind_amount
        # The server gives us our hole cards for the first hand here.
        # Store them so that on_round_start simply refreshes later.
        self.hole_cards = player_hands

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Update hole cards if the engine provides them per hand.
        # Tries multiple possible attribute names for compatibility.
        possible_fields = ["player_hands", "hole_cards", "hands"]
        for field in possible_fields:
            if hasattr(round_state, field):
                hands = getattr(round_state, field)
                # The attribute might be a dict keyed by player id or a list.
                if isinstance(hands, dict):
                    self.hole_cards = hands.get(str(self.id), hands.get(self.id, self.hole_cards))
                else:
                    self.hole_cards = hands
                break

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """
        Main decision method – selects an action plus amount (0 if not used).
        """
        # ---------------- Data extraction ---------------- #
        community = round_state.community_cards
        pot = round_state.pot
        cur_bet = round_state.current_bet
        min_raise = round_state.min_raise
        max_raise = min(round_state.max_raise, remaining_chips)
        player_bets: Dict[str, int] = round_state.player_bets or {}
        my_bet = player_bets.get(str(self.id), 0)
        to_call = max(0, cur_bet - my_bet)

        # ---------------- PREFLOP LOGIC ------------------ #
        if round_state.round.lower() == "preflop":
            action, amount = self._preflop_strategy(to_call, min_raise, max_raise, pot)
            return self._ensure_legal_action(action, amount, to_call, min_raise, max_raise)

        # ---------------- POSTFLOP LOGIC ----------------- #
        active_players = len(round_state.current_player)
        win_prob = self._estimate_equity(self.hole_cards, community, active_players)

        # Decide based on equity
        if win_prob >= self.AGGRO_THRESHOLD:
            # Big hand – either shove or big raise.
            if remaining_chips <= self.MIN_STACK_FOR_ALLIN * pot:
                return self._ensure_legal_action(PokerAction.ALL_IN, 0, to_call, min_raise, max_raise)
            else:
                target = int(min(max_raise, pot * self.RAISE_FACTOR))
                return self._ensure_legal_action(PokerAction.RAISE, target, to_call, min_raise, max_raise)
        elif win_prob >= self.CALL_THRESHOLD:
            # Medium strength -> call/check
            if to_call == 0:
                return PokerAction.CHECK, 0
            else:
                return self._ensure_legal_action(PokerAction.CALL, 0, to_call, min_raise, max_raise)
        else:
            # Weak -> fold/check
            if to_call == 0:
                return PokerAction.CHECK, 0
            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Nothing fancy – could add learning here.
        pass

    def on_end_game(
        self,
        round_state: RoundStateClient,
        player_score: float,
        all_scores: dict,
        active_players_hands: dict,
    ):
        # Persist any statistics if required (not used).
        pass

    # ------------------------------------------------------------------ #
    #  INTERNAL STRATEGY / UTILITY
    # ------------------------------------------------------------------ #
    def _preflop_strategy(
        self, to_call: int, min_raise: int, max_raise: int, pot: int
    ) -> Tuple[PokerAction, int]:
        """Very small pre-flop opening chart with position agnosticism."""
        card1, card2 = self.hole_cards
        rank1, suit1 = card1[0], card1[1]
        rank2, suit2 = card2[0], card2[1]
        suited = suit1 == suit2
        ranks = "".join(sorted([rank1, rank2], reverse=True))
        hand_key = f"{ranks}{'s' if suited else ''}"

        if hand_key in self.PREFLOP_PREMIUM:
            # Raise / 3-bet
            target = min(max_raise, max(min_raise * 3, pot + min_raise))
            return PokerAction.RAISE, target
        elif hand_key in self.PREFLOP_STRONG:
            if to_call == 0:
                target = min(max_raise, min_raise * 3)
                return PokerAction.RAISE, target
            else:
                # Facing raise – just call unless huge.
                return PokerAction.CALL, 0
        else:
            # Marginal hands limp if cheap, otherwise fold.
            if to_call == 0:
                return PokerAction.CHECK, 0
            elif to_call <= self.big_blind:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0

    # --------------- Equity calculation ---------------- #
    def _estimate_equity(
        self, hole_cards: List[str], community_cards: List[str], num_players: int
    ) -> float:
        """Monte-Carlo simulation of winning probability."""
        # Simple heuristic fallback
        if not _HAVE_TREYS:
            return self._heuristic_equity(hole_cards, community_cards, num_players)

        needed_community = 5 - len(community_cards)
        my_card_ints = [Card.new(c) for c in hole_cards]
        board_ints = [Card.new(c) for c in community_cards]

        wins = ties = 0
        iterations = self.MONTE_CARLO_ITERS
        evaluator = self.evaluator

        full_deck = Card.get_full_deck()
        dead_cards = set(my_card_ints + board_ints)

        for _ in range(iterations):
            deck = [c for c in full_deck if c not in dead_cards]
            random.shuffle(deck)

            # Draw remaining community
            drawn_community = deck[:needed_community]
            deck_pos = needed_community
            full_board = board_ints + drawn_community

            my_rank = evaluator.evaluate(full_board, my_card_ints)

            # Opponents
            won = True
            tie = False
            for _opp in range(num_players - 1):
                opp_hole = deck[deck_pos : deck_pos + 2]
                deck_pos += 2
                opp_rank = evaluator.evaluate(full_board, opp_hole)
                if opp_rank < my_rank:
                    won = False
                    break
                if opp_rank == my_rank:
                    tie = True
            if won:
                if tie:
                    ties += 1
                else:
                    wins += 1

        return (wins + ties * 0.5) / max(1, iterations)

    @staticmethod
    def _heuristic_equity(hole_cards: List[str], community_cards: List[str], players: int) -> float:
        """
        Extremely light-weight heuristic: counts pairs / suitedness.
        Returns equity approximation between 0-1.
        """
        card1, card2 = hole_cards
        p = 0.25  # base
        # Pair bonus
        if card1[0] == card2[0]:
            p += 0.25
        # Suited bonus
        if card1[1] == card2[1]:
            p += 0.05
        # High-card bonus
        high = {"A": 0.15, "K": 0.10, "Q": 0.08, "J": 0.06, "T": 0.04}
        p += high.get(card1[0], 0)
        p += high.get(card2[0], 0)
        # Board improvement – very naïve
        p += 0.03 * len(community_cards)
        # Multi-way penalty
        p = max(0.0, p - 0.05 * (players - 2))
        return min(1.0, p)

    # --------------- Safety guard ---------------------- #
    def _ensure_legal_action(
        self,
        action: PokerAction,
        amount: int,
        to_call: int,
        min_raise: int,
        max_raise: int,
    ) -> Tuple[PokerAction, int]:
        """
        Guarantees the returned action complies with engine requirements, else
        downgrades gracefully (e.g., RAISE→CALL, CALL→CHECK, …).
        """
        # Clamp amount into bounds
        amount = max(0, min(amount, max_raise))

        if action == PokerAction.RAISE:
            if amount < min_raise or amount <= to_call:
                # Invalid raise – fallback to call if possible
                if to_call > 0:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.CHECK, 0
            return action, amount

        if action == PokerAction.CALL and to_call == 0:
            return PokerAction.CHECK, 0

        if action == PokerAction.CHECK and to_call > 0:
            # Can't check – call if cheap, otherwise fold
            if to_call <= self.big_blind:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0

        # ALL_IN is always legal – no modification needed
        return action, amount