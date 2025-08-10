from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import random
import itertools
import math

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from enum import Enum

# Helper Enums for clarity if needed (not strictly necessary if imported from type)
class PokerRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

# ---------------------------
# Card utilities and evaluator
# ---------------------------

RANKS = "23456789TJQKA"
SUITS = "cdhs"
RANK_TO_INT: Dict[str, int] = {r: i + 2 for i, r in enumerate(RANKS)}  # '2' -> 2, ..., 'A' -> 14
INT_TO_RANK: Dict[int, str] = {v: k for k, v in RANK_TO_INT.items()}

# Precompute combinations indices for 7 choose 5 and 6 choose 5 to speed up
COMB_IDX_7_5 = list(itertools.combinations(range(7), 5))
COMB_IDX_6_5 = list(itertools.combinations(range(6), 5))

def make_deck() -> List[str]:
    return [r + s for r in RANKS for s in SUITS]

def parse_card(card: str) -> Tuple[int, str]:
    # card like 'Ah', 'Td'
    r = card[0].upper()
    s = card[1].lower()
    return RANK_TO_INT[r], s

def hand_rank_5(cards5: List[str]) -> Tuple[int, List[int]]:
    """
    Evaluate a 5-card poker hand.
    Returns a tuple: (category, tiebreakers...) higher is better.
    Categories: 8 SF, 7 Quads, 6 Full House, 5 Flush, 4 Straight, 3 Trips, 2 Two Pair, 1 Pair, 0 High card
    """
    # Parse
    ranks = []
    suits = []
    for c in cards5:
        ri, si = parse_card(c)
        ranks.append(ri)
        suits.append(si)
    ranks.sort(reverse=True)
    # Count ranks
    counts: Dict[int, int] = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    # Determine flush
    suit_counts: Dict[str, int] = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1
    is_flush = any(v == 5 for v in suit_counts.values())
    # Determine straight
    uniq = sorted(set(ranks), reverse=True)
    # Handle wheel straight A-2-3-4-5
    straight_high = 0
    if len(uniq) >= 5:
        # For exactly 5 cards, len(uniq) may be 5 or less (if duplicates)
        # Build a sequence from high to low
        u_desc = sorted(uniq, reverse=True)
        # Add wheel treatment by mapping Ace low
        # Check normal straight
        if u_desc[0] - u_desc[-1] == 4 and len(u_desc) == 5:
            # Could be straight, but there may be duplicates; since uniq it's fine
            if all(u_desc[i] - 1 == u_desc[i + 1] for i in range(4)):
                straight_high = u_desc[0]
        else:
            # General approach
            for i in range(len(u_desc) - 4):
                seq = u_desc[i:i + 5]
                if all(seq[j] - 1 == seq[j + 1] for j in range(4)):
                    straight_high = seq[0]
                    break
        # Wheel (A-5) check
        if straight_high == 0 and 14 in uniq:
            wheel = {14, 5, 4, 3, 2}
            if wheel.issubset(set(uniq)):
                straight_high = 5
    # Straight flush check
    if is_flush:
        flush_suit = max(suit_counts, key=lambda k: suit_counts[k])
        flush_cards = [parse_card(c)[0] for c in cards5 if c[1].lower() == flush_suit]
        flush_ranks = sorted(flush_cards, reverse=True)
        flush_uniq = sorted(set(flush_ranks), reverse=True)
        sf_high = 0
        if len(flush_uniq) >= 5:
            # There are exactly 5 cards in total, so flush_uniq should be length 5
            # But duplicates don't exist within flush_uniq
            u_desc = flush_uniq
            if u_desc[0] - u_desc[-1] == 4 and len(u_desc) == 5:
                if all(u_desc[i] - 1 == u_desc[i + 1] for i in range(4)):
                    sf_high = u_desc[0]
            else:
                for i in range(len(u_desc) - 4):
                    seq = u_desc[i:i + 5]
                    if all(seq[j] - 1 == seq[j + 1] for j in range(4)):
                        sf_high = seq[0]
                        break
            if sf_high == 0 and 14 in flush_uniq:
                if {14, 5, 4, 3, 2}.issubset(set(flush_uniq)):
                    sf_high = 5
        if sf_high:
            return (8, [sf_high])  # Straight flush, tiebreaker high card
    # Multiples (quads, full house, trips, pairs)
    # Sort by (count desc, rank desc)
    by_count = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    counts_sorted = [cnt for rnk, cnt in by_count]
    ranks_sorted_by_count = [rnk for rnk, cnt in by_count]
    if counts_sorted[0] == 4:
        # Four of a kind: quad rank, kicker
        quad_rank = ranks_sorted_by_count[0]
        kicker = max([r for r in ranks if r != quad_rank])
        return (7, [quad_rank, kicker])
    if counts_sorted[0] == 3 and counts_sorted[1] == 2:
        # Full house: trip rank, pair rank
        trip_rank = ranks_sorted_by_count[0]
        pair_rank = ranks_sorted_by_count[1]
        return (6, [trip_rank, pair_rank])
    if is_flush:
        # Flush: top five ranks (already 5 cards)
        return (5, sorted(ranks, reverse=True))
    if straight_high:
        return (4, [straight_high])
    if counts_sorted[0] == 3:
        # Trips: trip rank + top two kickers
        trip_rank = ranks_sorted_by_count[0]
        kickers = sorted([r for r in ranks if r != trip_rank], reverse=True)[:2]
        return (3, [trip_rank] + kickers)
    if counts_sorted[0] == 2 and counts_sorted[1] == 2:
        # Two pair: top pair rank, second pair rank, kicker
        pair1 = max([r for r, c in counts.items() if c == 2])
        pair2 = min([r for r, c in counts.items() if c == 2])
        kicker = max([r for r in ranks if r != pair1 and r != pair2])
        return (2, [pair1, pair2, kicker])
    if counts_sorted[0] == 2:
        # One pair: pair rank + top three kickers
        pair_rank = ranks_sorted_by_count[0]
        kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)[:3]
        return (1, [pair_rank] + kickers)
    # High card: five ranks
    return (0, sorted(ranks, reverse=True))

def best_hand_rank(cards: List[str]) -> Tuple[int, List[int]]:
    """
    Cards length 5-7. Returns best 5-card hand rank tuple using enumeration if needed.
    """
    n = len(cards)
    if n == 5:
        return hand_rank_5(cards)
    elif n == 6:
        best = None
        for idxs in COMB_IDX_6_5:
            pick = [cards[i] for i in idxs]
            r = hand_rank_5(pick)
            if (best is None) or (r > best):
                best = r
        return best
    elif n == 7:
        best = None
        for idxs in COMB_IDX_7_5:
            pick = [cards[i] for i in idxs]
            r = hand_rank_5(pick)
            if (best is None) or (r > best):
                best = r
        return best
    else:
        # Fallback for other sizes: enumerate all 5-card combos
        best = None
        for comb in itertools.combinations(range(n), 5):
            pick = [cards[i] for i in comb]
            r = hand_rank_5(pick)
            if (best is None) or (r > best):
                best = r
        return best

def compare_hands(cards_a: List[str], cards_b: List[str]) -> int:
    """
    Compare two hands (5-7 cards each including board).
    Return 1 if A>B, 0 if tie, -1 if A<B.
    """
    ra = best_hand_rank(cards_a)
    rb = best_hand_rank(cards_b)
    if ra > rb:
        return 1
    if rb > ra:
        return -1
    return 0

# ---------------------------
# Equity estimation
# ---------------------------

def chen_score(card1: str, card2: str) -> float:
    """
    Simplified Chen formula to get a rough preflop strength score.
    """
    r1, s1 = parse_card(card1)
    r2, s2 = parse_card(card2)
    hi = max(r1, r2)
    lo = min(r1, r2)
    suited = (card1[1].lower() == card2[1].lower())
    # Base highest card scores
    base_map = {
        14: 10.0, 13: 8.0, 12: 7.0, 11: 6.0,
        10: 5.0, 9: 4.5, 8: 4.0, 7: 3.5,
        6: 3.0, 5: 2.5, 4: 2.0, 3: 1.5, 2: 1.0
    }
    if r1 == r2:
        # Pair
        score = base_map[hi] * 2
        score = max(score, 5.0)  # minimum score for low pairs
        return score
    score = base_map[hi]
    # Suited adds
    if suited:
        score += 2.0
    # Gap penalties
    gap = (hi - lo - 1)
    if gap == 0:
        pass
    elif gap == 1:
        score -= 1.0
    elif gap == 2:
        score -= 2.0
    elif gap == 3:
        score -= 4.0
    else:
        score -= 5.0
    # Straight bonus for connectors / one-gap / two-gap if high enough
    if (gap <= 2) and (hi < 14) and (hi >= 5):
        score += 1.0
    # Round to nearest half
    return max(0.0, score)

def chen_to_equity_hu(score: float) -> float:
    """
    Rough mapping from Chen score to heads-up equity vs random.
    This is an approximation, returns value between ~0.35 and 0.8
    """
    # Ensure numeric
    s = max(0.0, float(score))
    # Map: 0 -> 0.38, 10 -> 0.53, 20 -> 0.66, 30 -> 0.76
    # Piecewise linear-ish using logistic-like function
    # equity ≈ 0.38 + 0.015*s + 0.0008*s^2, capped at 0.85
    e = 0.38 + 0.015 * s + 0.0008 * (s ** 2)
    return max(0.3, min(0.85, e))

def adjust_equity_for_multi(e_hu: float, opp_count: int) -> float:
    """
    Approximate equity versus multiple opponents assuming independence.
    """
    opp = max(1, opp_count)
    # P(beat all opp) ~ e_hu ** opp
    # But to soften, use blend with linear drop
    e_multi = (e_hu ** opp) * 0.7 + (max(0.0, e_hu - 0.05 * (opp - 1))) * 0.3
    return max(0.0, min(0.95, e_multi))

def estimate_equity_mc(my_cards: List[str], board_cards: List[str], opp_count: int, iters: int, rng: random.Random) -> float:
    """
    Monte Carlo equity estimation.
    """
    # Safety checks
    if not my_cards or len(my_cards) != 2:
        return 0.0
    opp = max(1, opp_count)
    deck = make_deck()
    known = set(my_cards + board_cards)
    deck = [c for c in deck if c not in known]
    if len(deck) < 2 * opp:
        # Not enough cards; return neutral-ish
        return 0.5

    wins = 0.0
    ties = 0.0
    total = 0.0
    # Pre-create list for sampling to avoid repeated building
    for _ in range(max(1, iters)):
        # Sample opponent hole cards and remaining board
        rng.shuffle(deck)
        # Opponents
        opp_holes = []
        idx = 0
        for _o in range(opp):
            opp_holes.append([deck[idx], deck[idx + 1]])
            idx += 2
        # Sample remaining community
        need_board = max(0, 5 - len(board_cards))
        rem_board = deck[idx: idx + need_board]
        # Our 7
        our_cards7 = my_cards + board_cards + rem_board
        our_rank = best_hand_rank(our_cards7)

        # Opponents compare
        best_vs = -1  # 1 if we win > all, 0 tie possible, -1 lose
        tie_with = 0
        lose = False
        for hole in opp_holes:
            opp_cards7 = hole + board_cards + rem_board
            cmp_res = 0
            rb = best_hand_rank(opp_cards7)
            if our_rank > rb:
                cmp_res = 1
            elif rb > our_rank:
                cmp_res = -1
            else:
                cmp_res = 0
            if cmp_res < 0:
                lose = True
                # break early
                best_vs = -1
                break
            elif cmp_res == 0:
                tie_with += 1
        if lose:
            total += 1.0
            continue
        # We didn't lose to any opponent
        if tie_with > 0:
            # Tie with at least one; assume pot split among ties+hero
            ties += 1.0
        else:
            wins += 1.0
        total += 1.0
    # Equity: wins + ties/ (ties + 1)? approximate: if tie_with opponents, hero's share ~ 1/(tie_with+1)
    # In our accounting, ties += 1 event. Approx equity = (wins + 0.5 * ties)/total as rough
    equity = (wins + 0.5 * ties) / (total + 1e-9)
    return max(0.0, min(1.0, equity))

# ---------------------------
# The Bot
# ---------------------------

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 0
        self.blind_amount = 0
        self.big_blind_player_id = None
        self.small_blind_player_id = None
        self.all_players: List[int] = []
        self.hands_played = 0
        self.total_profit = 0
        self.rng = random.Random(1337)
        # Track last round number to reset per-hand state
        self.current_round_num = -1
        # Attempt to track our current hole cards if provided anywhere
        self.my_hole_cards: List[str] = []
        # Aggression and memory
        self.last_action = None

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players[:] if all_players else []
        # If hands are provided (may not be per-hand), store for fallback
        # Expect two cards for our player possibly
        if isinstance(player_hands, list) and len(player_hands) >= 2:
            # Might be provided at start; but will quickly get outdated
            self.my_hole_cards = player_hands[:2]
        else:
            self.my_hole_cards = []

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Reset per-hand or per-round information
        self.last_action = None
        # Attempt to detect our hole cards from any accessible field
        self._update_hole_cards_from_context(round_state)

        # Track round number to detect new hand
        self.current_round_num = getattr(round_state, "round_num", self.current_round_num)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """
        # Fail-safe: Always ensure valid returns even under unexpected state.
        try:
            # Update hole cards if possible
            self._update_hole_cards_from_context(round_state)

            # Determine stage
            stage = self._get_stage(round_state)
            board_cards = round_state.community_cards or []
            my_bet = self._get_my_bet(round_state)
            to_call = max(0, int(round_state.current_bet) - int(my_bet))
            can_check = (to_call <= 0)
            pot = max(0, int(round_state.pot))
            min_raise = int(getattr(round_state, "min_raise", 0) or 0)
            max_raise = int(getattr(round_state, "max_raise", 0) or 0)
            # Active opponents
            opp_count = self._estimate_active_opponents(round_state)
            opp_count = max(1, opp_count)

            # If we don't know our hole cards, play ultra-conservative
            if not self.my_hole_cards or len(self.my_hole_cards) != 2:
                if can_check:
                    return (PokerAction.CHECK, 0)
                else:
                    return (PokerAction.FOLD, 0)

            # Equity estimation
            equity = self._estimate_equity(stage, self.my_hole_cards, board_cards, opp_count, round_state, to_call, pot)

            # Pot odds for calling decision
            pot_odds = to_call / (pot + to_call + 1e-9) if to_call > 0 else 0.0
            # Multiway adjustment: require higher equity when more players remain
            multi_adj = 0.02 * max(0, opp_count - 1)
            call_threshold = min(0.95, pot_odds + multi_adj + 0.02)

            # Stack to pot ratio heuristic
            spr = (remaining_chips + 1e-9) / (pot + 1e-9) if pot > 0 else 10.0

            # Decide action based on current situation
            # 1) If we can check (no bet to us)
            if can_check:
                # Consider betting/raising for value with strong hands
                # Use stage-dependent threshold
                value_thresh = 0.64 if stage == PokerRound.PREFLOP else (0.58 if stage == PokerRound.FLOP else (0.6 if stage == PokerRound.TURN else 0.62))
                if equity > value_thresh and min_raise > 0 and max_raise >= min_raise:
                    # If very strong and low SPR, consider all-in
                    if equity > 0.82 or (equity > 0.72 and spr <= 2.0 and max_raise > 0):
                        self.last_action = (PokerAction.ALL_IN, 0)
                        return self.last_action
                    # Otherwise raise minimum to keep it valid
                    amount = min(max(min_raise, 1), max_raise)
                    self.last_action = (PokerAction.RAISE, amount)
                    return self.last_action
                # Otherwise check
                self.last_action = (PokerAction.CHECK, 0)
                return self.last_action

            # 2) We are facing a bet (to_call > 0)
            # If equity insufficient, fold
            if equity + 1e-9 < call_threshold:
                self.last_action = (PokerAction.FOLD, 0)
                return self.last_action

            # If equity comfortably above threshold, consider raise
            # Margin above threshold
            margin = equity - call_threshold
            if min_raise > 0 and max_raise >= min_raise and margin > 0.12:
                # If we have very strong equity or low SPR, shove
                if (equity > 0.80 and spr <= 4.0 and max_raise > 0) or (equity > 0.88):
                    self.last_action = (PokerAction.ALL_IN, 0)
                    return self.last_action
                # Otherwise raise minimally to avoid invalid raise sizing
                amount = min(max(min_raise, 1), max_raise)
                self.last_action = (PokerAction.RAISE, amount)
                return self.last_action

            # Default: call
            self.last_action = (PokerAction.CALL, 0)
            return self.last_action

        except Exception:
            # Fail-safe: never crash; fold or check safely
            try:
                # If we can check, do so, else fold
                my_bet = self._get_my_bet(round_state)
                to_call = max(0, int(round_state.current_bet) - int(my_bet))
                if to_call <= 0:
                    return (PokerAction.CHECK, 0)
                return (PokerAction.FOLD, 0)
            except Exception:
                # Absolute fallback
                return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        try:
            self.hands_played += 1
            # Potentially track profit
            delta = int(remaining_chips) - int(self.starting_chips)
            self.total_profit += delta
            # Reset hand cards
            self.my_hole_cards = []
        except Exception:
            # Ensure no exception is thrown
            pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # No-op or could log internally; keep robust
        pass

    # ---------------------------
    # Helper methods
    # ---------------------------

    def _get_stage(self, round_state: RoundStateClient) -> PokerRound:
        stage_name = (round_state.round or "").lower()
        if stage_name == 'preflop':
            return PokerRound.PREFLOP
        elif stage_name == 'flop':
            return PokerRound.FLOP
        elif stage_name == 'turn':
            return PokerRound.TURN
        elif stage_name == 'river':
            return PokerRound.RIVER
        # Fallback by number of community cards
        cc = len(round_state.community_cards or [])
        if cc == 0:
            return PokerRound.PREFLOP
        if cc == 3:
            return PokerRound.FLOP
        if cc == 4:
            return PokerRound.TURN
        return PokerRound.RIVER

    def _get_my_bet(self, round_state: RoundStateClient) -> int:
        # player_bets: Dict[str, int]
        try:
            pid = str(self.id)
            return int(round_state.player_bets.get(pid, 0))
        except Exception:
            return 0

    def _estimate_active_opponents(self, round_state: RoundStateClient) -> int:
        """
        Estimate number of opponents still in the hand.
        """
        # Prefer current_player list if available
        try:
            active = list(round_state.current_player) if round_state.current_player else []
            # Remove self
            if self.id in active:
                active_count = len(active) - 1
                return max(1, active_count)
            # Else try from actions: exclude folds
            acts = round_state.player_actions or {}
            # Count players not explicitly folded
            not_folded = [pid for pid, act in acts.items() if str(act).lower() != 'fold']
            # If player_actions uses string keys
            if not_folded:
                # Opponents approx = count - 1
                if str(self.id) in not_folded:
                    return max(1, len(not_folded) - 1)
                return max(1, len(not_folded))
        except Exception:
            pass
        # Fallback to table size minus one
        if self.all_players:
            return max(1, len(self.all_players) - 1)
        # Default 1 opponent
        return 1

    def _update_hole_cards_from_context(self, round_state: RoundStateClient):
        """
        Attempt to retrieve our hole cards from any available attributes.
        This method is defensive: it checks multiple potential places without throwing.
        """
        # If already have valid cards for current hand (2 cards), keep them
        if isinstance(self.my_hole_cards, list) and len(self.my_hole_cards) == 2:
            # Basic validity check of format 'Rs'
            if all(isinstance(c, str) and len(c) == 2 for c in self.my_hole_cards):
                return

        # Try to fetch from round_state if it unexpectedly contains them
        try:
            if hasattr(round_state, "player_hands") and isinstance(round_state.player_hands, dict):
                # Expect mapping from player id to hand list
                hand = round_state.player_hands.get(str(self.id))
                if isinstance(hand, list) and len(hand) >= 2:
                    self.my_hole_cards = hand[:2]
                    return
        except Exception:
            pass

        # Try attributes possibly set by engine or Bot
        try:
            if hasattr(self, "hand") and isinstance(getattr(self, "hand"), list):
                hand = getattr(self, "hand")
                if len(hand) >= 2 and all(isinstance(c, str) and len(c) == 2 for c in hand[:2]):
                    self.my_hole_cards = hand[:2]
                    return
        except Exception:
            pass

        try:
            if hasattr(self, "hole_cards") and isinstance(getattr(self, "hole_cards"), list):
                hand = getattr(self, "hole_cards")
                if len(hand) >= 2 and all(isinstance(c, str) and len(c) == 2 for c in hand[:2]):
                    self.my_hole_cards = hand[:2]
                    return
        except Exception:
            pass

        try:
            if hasattr(self, "get_hand") and callable(getattr(self, "get_hand")):
                hand = getattr(self, "get_hand")()
                if isinstance(hand, list) and len(hand) >= 2:
                    self.my_hole_cards = hand[:2]
                    return
        except Exception:
            pass

        # Fallback: keep as is (may be empty); decisions will be conservative without cards

    def _estimate_equity(self, stage: PokerRound, my_cards: List[str], board_cards: List[str], opp_count: int, round_state: RoundStateClient, to_call: int, pot: int) -> float:
        """
        Stage-aware equity estimation with adaptive MC iterations.
        """
        # Preflop
        if stage == PokerRound.PREFLOP:
            # If heavy action (large to_call vs pot), do MC more iterations
            pressure = 0.0
            try:
                pressure = to_call / (pot + to_call + 1e-9)
            except Exception:
                pressure = 0.0
            # Base iterations
            base_iters = 120
            if pressure > 0.4:
                base_iters = 180
            if opp_count >= 3:
                base_iters = max(base_iters - 30, 80)
            # Ensure performance bounds
            base_iters = int(max(60, min(220, base_iters)))
            # MC preflop
            e_mc = estimate_equity_mc(my_cards, [], opp_count, base_iters, self.rng)
            return max(0.0, min(1.0, e_mc))

        # Postflop
        # More board info -> fewer unknowns -> fewer iters needed
        cc = len(board_cards or [])
        if cc == 3:
            iters = 220
        elif cc == 4:
            iters = 260
        else:
            iters = 320
        # Adjust for opp count
        if opp_count >= 3:
            iters = max(160, iters - 40)
        # Ensure not too high
        iters = int(min(400, max(120, iters)))
        e_post = estimate_equity_mc(my_cards, board_cards, opp_count, iters, self.rng)
        return max(0.0, min(1.0, e_post))