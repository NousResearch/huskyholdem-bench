from __future__ import annotations

import random
from typing import Dict, List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


# ----------  Helper utilities ---------- #
RANK_CHAR_TO_INT = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}


def card_to_rank(card: str) -> int:
    """Return numerical rank from a card string such as 'Ah'."""
    return RANK_CHAR_TO_INT[card[0]]


def is_suited(card1: str, card2: str) -> bool:
    return card1[1] == card2[1]


def classify_preflop(hand: Tuple[str, str]) -> int:
    """
    Return a numeric strength category for a starting hand.
    3 – premium, 2 – strong, 1 – medium, 0 – weak
    """
    c1, c2 = hand
    r1, r2 = card_to_rank(c1), card_to_rank(c2)
    suited = is_suited(c1, c2)

    # pairs
    if r1 == r2:
        if r1 >= 10:  # TT+
            return 3
        elif 8 <= r1 <= 9:  # 88/99
            return 2
        elif 6 <= r1 <= 7:  # 66/77
            return 1
        else:
            return 0

    high = max(r1, r2)
    low = min(r1, r2)

    # suited big cards
    if suited:
        if {high, low} == {14, 13}:  # AKs
            return 3
        if high == 14 and low >= 11:  # AQ/AJ suited
            return 2
        if (high == 13 and low >= 11) or (high == 12 and low >= 11):  # KQ/QJ/JT suited
            return 1
        if high >= 11 and low >= 9:  # broadway suited connectors
            return 1

    # offsuit big combos
    if not suited:
        if {high, low} == {14, 13}:  # AKo
            return 2
        if high == 14 and low >= 12:  # AQo+
            return 1
        if high == 13 and low >= 12:  # KQo
            return 1

    # suited connectors 65s+
    if suited and high - low == 1 and low >= 6:
        return 1

    return 0


def evaluate_simple_postflop(hole: Tuple[str, str], community: List[str]) -> int:
    """
    Extremely light-weight post-flop evaluator.

    0 – nothing
    1 – one pair
    2 – two pair / trips or better (considered strong)
    """
    cards = list(hole) + community
    ranks = [card_to_rank(c) for c in cards]
    counts: Dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1

    max_same = max(counts.values())
    if max_same >= 3:
        return 2  # trips or better
    if max_same == 2:
        # Check how many different ranks make pairs
        pairs = sum(1 for v in counts.values() if v == 2)
        if pairs >= 2:
            return 2  # two pair
        return 1  # single pair

    # draw detection can be added; keep simple for robustness
    return 0


# ----------  Bot implementation ---------- #
class SimplePlayer(Bot):
    """
    A light-weight rule-based bot.
    """

    def __init__(self):
        super().__init__()
        self.big_blind: int = 0
        self.small_blind: int = 0
        self.hole_cards: Tuple[str, str] | None = None
        self.last_round_num: int | None = None

    # ----------  Framework hooks ---------- #
    def on_start(
        self,
        starting_chips: int,
        player_hands: List[str],
        blind_amount: int,
        big_blind_player_id: int,
        small_blind_player_id: int,
        all_players: List[int],
    ):
        # In the framework, `blind_amount` represents the big blind.
        self.big_blind = blind_amount
        self.small_blind = blind_amount // 2 if blind_amount > 1 else 1
        # Store initial hole cards if provided
        if player_hands and len(player_hands) >= 2:
            self.hole_cards = (player_hands[0], player_hands[1])

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """
        Expect the engine to refresh the player's hole cards inside `round_state`
        (commonly via an extra field). We extract defensively.
        """
        self.last_round_num = round_state.round_num
        self._update_hole_cards_from_state(round_state)

    def get_action(
        self, round_state: RoundStateClient, remaining_chips: int
    ) -> Tuple[PokerAction, int]:
        """
        Core decision logic. Always returns a valid action/amount pair.
        """
        # Defensive – ensure we always have our current hole cards.
        self._update_hole_cards_from_state(round_state)
        if not self.hole_cards:
            # If for some reason cards missing – fold to stay safe.
            return PokerAction.FOLD, 0

        my_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = max(0, round_state.current_bet - my_bet)
        pot = max(1, round_state.pot)  # avoid /0

        # ---- Pre-flop decision ---- #
        if round_state.round.lower() == "preflop":
            strength = classify_preflop(self.hole_cards)

            # Case 1 – nothing to call
            if to_call == 0:
                if strength >= 2:
                    # Open raise 3×BB or minimum raise
                    raise_size = max(round_state.min_raise, 3 * self.big_blind)
                    raise_size = min(raise_size, round_state.max_raise, remaining_chips)
                    if raise_size >= round_state.min_raise:
                        return PokerAction.RAISE, raise_size
                # Otherwise limp/check
                return PokerAction.CHECK, 0

            # Case 2 – facing a raise
            else:
                # Pot odds check – call small raises with decent hands
                if strength == 3:
                    # Occasionally 3-bet / shove
                    if random.random() < 0.4 and remaining_chips > 0:
                        raise_size = min(
                            max(round_state.min_raise, to_call * 3),
                            remaining_chips,
                            round_state.max_raise,
                        )
                        if raise_size >= round_state.min_raise:
                            return PokerAction.RAISE, raise_size
                    # Else just call
                    return PokerAction.CALL, 0

                if strength == 2 and to_call <= 4 * self.big_blind:
                    return PokerAction.CALL, 0

                if strength == 1 and to_call <= 2 * self.big_blind:
                    return PokerAction.CALL, 0

                return PokerAction.FOLD, 0

        # ---- Post-flop decision ---- #
        made_value = evaluate_simple_postflop(self.hole_cards, round_state.community_cards)

        # No bet to us
        if to_call == 0:
            if made_value >= 2:
                # Strong hand – value bet about 60% pot
                bet_amount = int(pot * 0.6)
                bet_amount = max(round_state.min_raise, bet_amount)
                bet_amount = min(bet_amount, remaining_chips, round_state.max_raise)
                if bet_amount >= round_state.min_raise:
                    return PokerAction.RAISE, bet_amount
                return PokerAction.CHECK, 0

            if made_value == 1:
                # Medium strength – small bet 30 % pot with some frequency
                if random.random() < 0.5:
                    bet_amount = int(pot * 0.3)
                    bet_amount = max(round_state.min_raise, bet_amount)
                    bet_amount = min(bet_amount, remaining_chips, round_state.max_raise)
                    if bet_amount >= round_state.min_raise:
                        return PokerAction.RAISE, bet_amount
                return PokerAction.CHECK, 0

            # Nothing – just check
            return PokerAction.CHECK, 0

        # There is a wager to us
        else:
            if made_value >= 2:
                # Strong – raise or call
                if random.random() < 0.5:
                    raise_amt = max(round_state.min_raise, to_call * 2)
                    raise_amt = min(raise_amt, remaining_chips, round_state.max_raise)
                    if raise_amt >= round_state.min_raise:
                        return PokerAction.RAISE, raise_amt
                return PokerAction.CALL, 0

            if made_value == 1:
                # Call small bets, fold large ones
                if to_call <= pot * 0.4 or to_call <= self.big_blind * 4:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0

            # Bluff occasionally if cheap
            if to_call <= self.big_blind and random.random() < 0.1:
                raise_amt = max(round_state.min_raise, to_call * 3)
                raise_amt = min(raise_amt, remaining_chips, round_state.max_raise)
                if raise_amt >= round_state.min_raise:
                    return PokerAction.RAISE, raise_amt

            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Clear hole cards for the next round
        self.hole_cards = None

    def on_end_game(
        self,
        round_state: RoundStateClient,
        player_score: float,
        all_scores: dict,
        active_players_hands: dict,
    ):
        # Nothing to persist between games for this simple bot
        pass

    # ----------  Internal helpers ---------- #
    def _update_hole_cards_from_state(self, round_state: RoundStateClient):
        """
        Extracts hole cards from any plausible attribute within the round_state.
        Different engines sometimes expose them differently, so we attempt a few
        common patterns but always fail-safe.
        """
        if hasattr(round_state, "player_hands"):
            ph = getattr(round_state, "player_hands")
            if isinstance(ph, dict):
                cards = ph.get(str(self.id)) or ph.get(self.id)
                if cards and len(cards) >= 2:
                    self.hole_cards = (cards[0], cards[1])
            elif isinstance(ph, list) and len(ph) >= 2:
                # Heads-up convenience
                self.hole_cards = (ph[0], ph[1])

        # Some engines use "hole_cards"
        if self.hole_cards is None and hasattr(round_state, "hole_cards"):
            hc = getattr(round_state, "hole_cards")
            if isinstance(hc, dict):
                cards = hc.get(str(self.id)) or hc.get(self.id)
                if cards and len(cards) >= 2:
                    self.hole_cards = (cards[0], cards[1])
            elif isinstance(hc, list) and len(hc) >= 2:
                self.hole_cards = (hc[0], hc[1])