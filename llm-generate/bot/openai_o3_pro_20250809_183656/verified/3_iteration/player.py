# player.py
from __future__ import annotations

import itertools
import math
import random
from typing import Dict, List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


RANK_ORDER = "23456789TJQKA"
RANK_VALUE = {r: i for i, r in enumerate(RANK_ORDER, start=2)}
SUITS = ["c", "d", "h", "s"]


def _card_rank(card: str) -> int:
    return RANK_VALUE[card[0]]


def _card_suit(card: str) -> str:
    return card[1]


def _is_straight(ranks: List[int]) -> Tuple[bool, int]:
    """Return (is_straight, highest_rank_in_straight)."""
    # wheel straight
    wheel = {14, 5, 4, 3, 2}
    unique = sorted(set(ranks), reverse=True)
    # Add wheel low Ace (value 1)
    if 14 in unique:
        unique.append(1)
    for i in range(len(unique) - 4):
        window = unique[i : i + 5]
        if max(window) - min(window) == 4 and len(window) == 5:
            return True, max(window)
        if set(window) == wheel:
            return True, 5
    return False, 0


def evaluate_5(cards: List[str]) -> Tuple[int, List[int]]:
    """Evaluate exactly 5 cards. Return (category, tiebreaker list). Higher better.
    Category mapping:
        8: Straight Flush
        7: Four of a Kind
        6: Full House
        5: Flush
        4: Straight
        3: Three of a Kind
        2: Two Pair
        1: Pair
        0: High Card
    """
    ranks = [_card_rank(c) for c in cards]
    suits = [_card_suit(c) for c in cards]
    rank_count: Dict[int, int] = {}
    for r in ranks:
        rank_count[r] = rank_count.get(r, 0) + 1
    counts = sorted(rank_count.values(), reverse=True)
    sorted_ranks_desc = sorted(ranks, reverse=True)

    is_flush = len(set(suits)) == 1
    is_straight, highest_in_straight = _is_straight(ranks)

    if is_flush and is_straight:
        return 8, [highest_in_straight]
    if counts[0] == 4:
        quad_rank = max(rank_count, key=lambda r: (rank_count[r] == 4, r))
        kicker = max([r for r in ranks if r != quad_rank])
        return 7, [quad_rank, kicker]
    if counts[0] == 3 and counts[1] == 2:
        trips_rank = max(rank_count, key=lambda r: (rank_count[r] == 3, r))
        pair_rank = max([r for r, c in rank_count.items() if c == 2])
        return 6, [trips_rank, pair_rank]
    if is_flush:
        return 5, sorted_ranks_desc
    if is_straight:
        return 4, [highest_in_straight]
    if counts[0] == 3:
        trips_rank = max(rank_count, key=lambda r: (rank_count[r] == 3, r))
        kickers = sorted([r for r in ranks if r != trips_rank], reverse=True)
        return 3, [trips_rank] + kickers
    if counts[0] == 2 and counts[1] == 2:
        pair_ranks = sorted([r for r, c in rank_count.items() if c == 2], reverse=True)
        kicker = max([r for r in ranks if r not in pair_ranks])
        return 2, pair_ranks + [kicker]
    if counts[0] == 2:
        pair_rank = max([r for r, c in rank_count.items() if c == 2])
        kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
        return 1, [pair_rank] + kickers
    return 0, sorted_ranks_desc


def evaluate_best(cards: List[str]) -> Tuple[int, List[int]]:
    """Evaluate best 5-card hand among 5–7 cards."""
    best: Tuple[int, List[int]] = (-1, [])
    for combo in itertools.combinations(cards, 5):
        score = evaluate_5(list(combo))
        if score > best:
            best = score
    return best


def chen_formula(card1: str, card2: str) -> float:
    """ Approximate pre-flop strength using Chen formula (simplified). """
    r1 = _card_rank(card1)
    r2 = _card_rank(card2)
    high = max(r1, r2)
    low = min(r1, r2)
    values = {14: 10, 13: 8, 12: 7, 11: 6, 10: 5, 9: 4.5, 8: 4, 7: 3.5, 6: 3,
              5: 2.5, 4: 2, 3: 1.5, 2: 1}
    pts = values[high]

    # Pair
    if r1 == r2:
        pts = max(5, pts * 2)

    # Suited
    if _card_suit(card1) == _card_suit(card2) and r1 != r2:
        pts += 2

    # Gap
    gap = abs(r1 - r2) - 1
    gap_penalty = {0: 0, 1: 1, 2: 2, 3: 4}
    pts -= gap_penalty.get(gap, 5)

    # Bonus for small gap with high cards
    if gap <= 1 and high >= 12 and r1 != r2:
        pts += 1

    return max(0, pts)


class SimplePlayer(Bot):
    """
    A reasonably tight-aggressive bot:
    - Uses Chen formula pre-flop
    - Evaluates made hand post-flop
    - Acts conservatively when weak and bets / raises when strong
    """

    def __init__(self):
        super().__init__()
        self.starting_chips: int | None = None
        self.big_blind: int | None = None
        self.small_blind: int | None = None
        self.hole_cards: List[str] = []
        self.round_number: int = 0

    # ---------- Helper utilities ---------- #

    def _my_bet(self, state: RoundStateClient) -> int:
        return state.player_bets.get(str(self.id), 0)

    def _call_cost(self, state: RoundStateClient) -> int:
        return max(0, state.current_bet - self._my_bet(state))

    def _can_check(self, state: RoundStateClient) -> bool:
        return self._call_cost(state) == 0

    def _extract_hole_cards(self, state: RoundStateClient) -> List[str]:
        """
        Tries multiple attribute names to fetch private hole cards.
        Falls back to stored value if the framework doesn’t expose them.
        """
        for key in ("hole_cards", "hand", "hole_card", "player_hands"):
            if hasattr(state, key):
                data = getattr(state, key)
                # player_hands may be a dict
                if isinstance(data, dict):
                    return data.get(str(self.id), self.hole_cards)
                if isinstance(data, list):
                    return data
        return self.hole_cards

    # ---------- Abstract method overrides ---------- #

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
        self.big_blind = blind_amount
        self.small_blind = blind_amount // 2
        self.hole_cards = player_hands
        # store id maybe set externally later
        # no further action needed

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.round_number = round_state.round_num
        self.hole_cards = self._extract_hole_cards(round_state)

    def get_action(
        self, round_state: RoundStateClient, remaining_chips: int
    ) -> Tuple[PokerAction, int]:
        try:
            self.hole_cards = self._extract_hole_cards(round_state)
            round_name = round_state.round.lower()
            call_amount = self._call_cost(round_state)
            pot = max(round_state.pot, 1)  # avoid zero
            min_raise = round_state.min_raise
            max_raise = round_state.max_raise

            # ---------- Pre-flop ---------- #
            if round_name == "preflop":
                strength = chen_formula(*self.hole_cards)
                num_players = len(round_state.current_player)
                # heads-up loosen threshold
                threshold_raise = 7 if num_players > 2 else 6
                threshold_call = 5 if num_players > 2 else 4

                # Someone raised heavily?
                expensive = call_amount > 5 * self.big_blind

                if strength >= threshold_raise and not expensive:
                    # Aggressive play: raise 3–4 BB or min_raise
                    raise_size = max(min_raise, 3 * self.big_blind)
                    raise_size = min(raise_size, max_raise)
                    if raise_size > call_amount:
                        return PokerAction.RAISE, raise_size
                if strength >= threshold_call and call_amount <= 2 * self.big_blind:
                    if call_amount == 0:
                        return PokerAction.CHECK, 0
                    return PokerAction.CALL, 0
                # Fold otherwise
                if call_amount == 0:
                    return PokerAction.CHECK, 0
                return PokerAction.FOLD, 0

            # ---------- Post-flop (Flop / Turn / River) ---------- #
            cards = self.hole_cards + round_state.community_cards
            category, tiebreak = evaluate_best(cards)

            # Determine aggressiveness by hand category
            strong_made = category >= 4  # Straight or better
            medium_made = category == 3 or category == 2  # Trips / Two pair
            weak_pair = category == 1  # one pair

            if strong_made:
                # Value bet / raise
                desired_bet = int(pot * 0.7)
                raise_amount = max(min_raise, desired_bet - self._my_bet(round_state))
                raise_amount = min(raise_amount, max_raise)
                if raise_amount > call_amount and raise_amount >= min_raise:
                    return PokerAction.RAISE, raise_amount
                if call_amount == 0:
                    return PokerAction.CHECK, 0
                return PokerAction.CALL, 0

            if medium_made:
                # Call small bets, raise minimally if cheap
                if call_amount <= int(pot * 0.25):
                    if call_amount == 0:
                        # thin value bet small
                        desired = max(min_raise, int(pot * 0.5))
                        if desired <= max_raise and desired >= min_raise:
                            return PokerAction.RAISE, desired
                        return PokerAction.CHECK, 0
                    return PokerAction.CALL, 0
                # Too expensive
                return (
                    PokerAction.FOLD,
                    0,
                )

            if weak_pair:
                # very cautious
                if call_amount == 0:
                    return PokerAction.CHECK, 0
                if call_amount <= int(pot * 0.15):
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0

            # No made hand – only continue if we can check
            if self._can_check(round_state):
                return PokerAction.CHECK, 0
            # Bluff occasionally with very small probability if pot small
            if pot <= 4 * self.big_blind and random.random() < 0.05:
                bluff_amount = max(min_raise, int(pot * 0.75))
                bluff_amount = min(bluff_amount, max_raise)
                if bluff_amount >= min_raise:
                    return PokerAction.RAISE, bluff_amount
            return PokerAction.FOLD, 0
        except Exception:
            # Fallback safe action
            if self._can_check(round_state):
                return PokerAction.CHECK, 0
            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Nothing to clean up besides maybe updating memory
        pass

    def on_end_game(
        self,
        round_state: RoundStateClient,
        player_score: float,
        all_scores: dict,
        active_players_hands: dict,
    ):
        # Persist nothing between games
        pass