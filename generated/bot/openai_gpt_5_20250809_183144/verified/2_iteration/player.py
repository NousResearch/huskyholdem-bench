from typing import List, Tuple, Dict, Any, Optional
import random

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


def _rank_value(card: str) -> int:
    if not card or len(card) < 1:
        return 0
    r = card[0].upper()
    if r == 'A':
        return 14
    if r == 'K':
        return 13
    if r == 'Q':
        return 12
    if r == 'J':
        return 11
    if r == 'T':
        return 10
    # digits
    try:
        return int(r)
    except Exception:
        return 0


def _suit_value(card: str) -> str:
    if not card or len(card) < 2:
        return ''
    return card[1].lower()


def _safe_div(a: float, b: float) -> float:
    return a / (b + 1e-9)


class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips: int = 0
        self.blind_amount: int = 0
        self.big_blind_player_id: Optional[int] = None
        self.small_blind_player_id: Optional[int] = None
        self.all_players: List[int] = []
        self.hole_cards: List[str] = []
        self.rng = random.Random(1337)
        self.last_round_num: Optional[int] = None
        self.hand_played_round_num: Optional[int] = None
        self.debug: bool = False  # Set to True to enable internal logging if desired

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        # Initialize game state. Attempt to capture hole cards if provided.
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players[:] if all_players else []
        # Store hole cards if given (expected 2 cards like ['Ah','Kd'])
        if player_hands and isinstance(player_hands, list):
            # Only keep first 2 cards if more are present
            self.hole_cards = player_hands[:2]
        else:
            self.hole_cards = []
        # Reset per-hand trackers
        self.hand_played_round_num = None

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Called at the start of each betting street.
        # Some environments may call this at the start of a hand (preflop) with hole cards already set in on_start.
        # We keep state minimal here.
        self.last_round_num = round_state.round_num

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """

        # Defensive defaults
        try:
            street = (round_state.round or "").lower()
        except Exception:
            street = ""

        # My current bet on this street
        my_id_str = str(self.id) if self.id is not None else None
        try:
            my_street_bet = round_state.player_bets.get(my_id_str, 0) if my_id_str else 0
        except Exception:
            my_street_bet = 0

        current_bet = max(0, int(round_state.current_bet)) if hasattr(round_state, "current_bet") else 0
        call_cost = max(0, current_bet - my_street_bet)

        pot = int(round_state.pot) if hasattr(round_state, "pot") else 0
        min_raise_amt = int(round_state.min_raise) if hasattr(round_state, "min_raise") else 0
        max_raise_amt = int(round_state.max_raise) if hasattr(round_state, "max_raise") else remaining_chips

        can_check = call_cost <= 0

        # Compute table size estimate
        num_players = self._estimate_active_players(round_state)

        # Estimate hand strength
        strength = self._estimate_strength(street, self.hole_cards, round_state.community_cards, num_players)

        # Apply simple action strategy
        # Basic thresholds tuned conservatively
        preflop_open_raise_thr = 0.72 if num_players <= 3 else 0.78
        preflop_call_thr = 0.55 if num_players <= 3 else 0.60

        postflop_bet_thr = 0.70
        postflop_raise_thr = 0.82
        postflop_shove_thr = 0.95

        # Pot odds for calls
        call_pot_odds = _safe_div(call_cost, pot + call_cost)

        # Occasionally add small randomization to avoid predictability
        noise = (self.rng.random() - 0.5) * 0.04  # +/- 0.02
        strength_noisy = max(0.0, min(1.0, strength + noise))

        # Preflop logic
        if street == "preflop":
            # If we can check (e.g., BB and no raise)
            if can_check:
                # Open raise with strong hands, else check
                if self._can_raise(min_raise_amt, max_raise_amt, remaining_chips) and strength_noisy >= preflop_open_raise_thr:
                    amt = self._choose_raise_amount(min_raise_amt, max_raise_amt, remaining_chips, pot, current_bet, target="open")
                    if amt > 0:
                        return PokerAction.RAISE, amt
                return PokerAction.CHECK, 0
            else:
                # Facing a raise
                # If the call would exceed our stack, treat as all-in decision
                if call_cost >= remaining_chips:
                    if strength_noisy >= max(0.70, preflop_call_thr + 0.1):  # only shove with decent hands
                        return PokerAction.ALL_IN, 0
                    else:
                        return PokerAction.FOLD, 0

                # Call based on strength vs implied odds
                if strength_noisy >= max(preflop_call_thr, call_pot_odds + 0.15):
                    # Occasional 3-bet with top hands
                    if self._can_raise(min_raise_amt, max_raise_amt, remaining_chips) and strength_noisy >= 0.86 and self.rng.random() < 0.5:
                        amt = self._choose_raise_amount(min_raise_amt, max_raise_amt, remaining_chips, pot, current_bet, target="3bet")
                        if amt > 0:
                            return PokerAction.RAISE, amt
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0

        # Postflop logic (Flop/Turn/River)
        else:
            # If we can check
            if can_check:
                # Value bet or semi-bluff
                if self._can_raise(min_raise_amt, max_raise_amt, remaining_chips) and strength_noisy >= postflop_bet_thr:
                    amt = self._choose_raise_amount(min_raise_amt, max_raise_amt, remaining_chips, pot, current_bet, target="value")
                    if amt > 0:
                        return PokerAction.RAISE, amt
                # Semi-bluff occasionally with medium strength (draws)
                if self._can_raise(min_raise_amt, max_raise_amt, remaining_chips) and 0.45 <= strength_noisy < postflop_bet_thr and self.rng.random() < 0.25:
                    amt = self._choose_raise_amount(min_raise_amt, max_raise_amt, remaining_chips, pot, current_bet, target="semi")
                    if amt > 0:
                        return PokerAction.RAISE, amt
                return PokerAction.CHECK, 0
            else:
                # Facing a bet
                # If call would be all-in
                if call_cost >= remaining_chips:
                    # Only go all-in with strong hands
                    if strength_noisy >= max(0.72, postflop_raise_thr - 0.06):
                        return PokerAction.ALL_IN, 0
                    else:
                        return PokerAction.FOLD, 0

                # Raise with very strong hands
                if self._can_raise(min_raise_amt, max_raise_amt, remaining_chips) and strength_noisy >= postflop_raise_thr:
                    # Sometimes shove if extremely strong or short SPR (stack-to-pot)
                    spr = _safe_div(remaining_chips, pot + call_cost)
                    if strength_noisy >= postflop_shove_thr and spr <= 3 and remaining_chips > min_raise_amt:
                        return PokerAction.ALL_IN, 0
                    amt = self._choose_raise_amount(min_raise_amt, max_raise_amt, remaining_chips, pot, current_bet, target="value")
                    if amt > 0:
                        return PokerAction.RAISE, amt

                # Call if pot odds support it
                # Margin encourages folding marginal hands vs bets
                margin = 0.10
                if strength_noisy >= call_pot_odds + margin:
                    return PokerAction.CALL, 0

                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        # Reset hand-specific data if a new round will start next
        self.hole_cards = []  # Will be set by on_start if provided for next hand
        self.hand_played_round_num = None

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # No persistent learning; keep stateless for safety.
        pass

    # ---------- Helper methods below ----------

    def _estimate_active_players(self, round_state: RoundStateClient) -> int:
        # Try to estimate number of active players from round_state
        try:
            if hasattr(round_state, "player_actions") and isinstance(round_state.player_actions, dict):
                # Count players who have not folded (or all players in actions if no folds recorded)
                actions = round_state.player_actions
                num_all = len(actions) if actions else 0
                if num_all == 0:
                    return max(2, len(self.all_players)) if self.all_players else 2
                cnt_active = 0
                for pid, act in actions.items():
                    if not isinstance(act, str):
                        cnt_active += 1
                    else:
                        if act.lower() != "fold":
                            cnt_active += 1
                return max(2, cnt_active)
            else:
                return max(2, len(self.all_players)) if self.all_players else 2
        except Exception:
            return max(2, len(self.all_players)) if self.all_players else 2

    def _can_raise(self, min_raise_amt: int, max_raise_amt: int, remaining_chips: int) -> bool:
        if min_raise_amt is None or max_raise_amt is None:
            return False
        if min_raise_amt <= 0:
            return False
        # Can't raise more than we have
        if remaining_chips <= 0:
            return False
        # Max raise is capped by stack; ensure min <= max and <= remaining
        return min_raise_amt <= max_raise_amt and min_raise_amt <= remaining_chips

    def _choose_raise_amount(self, min_raise_amt: int, max_raise_amt: int, remaining_chips: int, pot: int, current_bet: int, target: str = "value") -> int:
        # Safe baseline: min raise
        amt = min_raise_amt

        # Slightly scale with pot for value raises
        if target in ("value", "3bet", "open", "semi"):
            # A conservative size selection within [min_raise, max_raise]
            size = min_raise_amt
            if target == "open":
                # Open to ~3x if possible
                size = max(min_raise_amt, min(max_raise_amt, int(max(2 * min_raise_amt, self.blind_amount * 3 or min_raise_amt))))
            elif target == "3bet":
                # 3-bet to ~2.5x the current bet increment if possible
                size = max(min_raise_amt, min(max_raise_amt, int(min_raise_amt * 2.5)))
            elif target == "value":
                # Postflop, raise about 2/3 pot if possible
                desired = int(0.66 * max(1, pot))
                size = max(min_raise_amt, min(max_raise_amt, desired))
            elif target == "semi":
                # Semi-bluff smaller sizing about 1/2 pot
                desired = int(0.5 * max(1, pot))
                size = max(min_raise_amt, min(max_raise_amt, desired))

            # Ensure final size respects stack
            size = min(size, remaining_chips)
            if size >= min_raise_amt:
                amt = size

        # Final safety clamp
        amt = max(min_raise_amt, min(max_raise_amt, amt))
        if amt > remaining_chips:
            amt = remaining_chips  # If we can't cover the raise as increment, we should consider ALL_IN upstream; use min to stay valid.
        # Make sure it's a positive integer
        amt = int(max(0, amt))
        # If still invalid, return 0 so caller can fallback to non-raise
        return amt if amt >= min_raise_amt else 0

    def _estimate_strength(self, street: str, hole: List[str], board: List[str], num_players: int) -> float:
        # Fallback when we somehow don't have hole cards
        if not hole or len(hole) < 2:
            # Without info, play very tight
            base_unknown = 0.30
            if street.lower() == "preflop":
                return base_unknown
            else:
                # Postflop without hole cards -> be conservative
                return 0.25

        street_l = (street or "").lower()
        if street_l == "preflop":
            return self._preflop_strength(hole, num_players)
        else:
            return self._postflop_strength(hole, board, num_players, street_l)

    def _preflop_strength(self, hole: List[str], num_players: int) -> float:
        a, b = hole[0], hole[1]
        r1, r2 = _rank_value(a), _rank_value(b)
        s1, s2 = _suit_value(a), _suit_value(b)
        suited = (s1 == s2 and s1 != '')

        hi = max(r1, r2)
        lo = min(r1, r2)
        gap = hi - lo

        # Pair
        if r1 == r2 and r1 > 0:
            # 22 -> 0.55, AA -> 0.98
            strength = 0.55 + (hi - 2) / 12.0 * 0.43
        else:
            # High card contribution
            base = max(0.0, (hi - 8) / 6.0) * 0.35 + max(0.0, (lo - 5) / 9.0) * 0.20
            # Suited bonus
            if suited:
                base += 0.06
            # Connectivity bonus/penalty
            if gap == 1:
                base += 0.06
            elif gap == 2:
                base += 0.03
            elif gap >= 4:
                base -= min(0.12, 0.03 * (gap - 3))
            # Ace or King high small bonus
            if hi >= 13:
                base += 0.03
            strength = max(0.10, min(0.92, base))

        # Heads-up vs multi-way adjustment
        if num_players <= 2:
            strength = min(0.99, strength + 0.08)
        elif num_players == 3:
            strength = min(0.99, strength + 0.03)
        else:
            strength = max(0.05, strength - 0.02 * (num_players - 3))

        # Strong suited broadway bumps
        if suited and ((hi >= 13 and lo >= 10) or (hi == 14 and lo >= 9)):
            strength = min(0.99, strength + 0.04)

        return float(max(0.0, min(1.0, strength)))

    def _postflop_strength(self, hole: List[str], board: List[str], num_players: int, street_l: str) -> float:
        # Combine cards
        cards = hole + (board or [])
        ranks = [_rank_value(c) for c in cards if c]
        suits = [_suit_value(c) for c in cards if c]
        board_ranks = [_rank_value(c) for c in (board or []) if c]
        board_suits = [_suit_value(c) for c in (board or []) if c]
        r1, r2 = _rank_value(hole[0]), _rank_value(hole[1])
        s1, s2 = _suit_value(hole[0]), _suit_value(hole[1])

        counts: Dict[int, int] = {}
        for r in ranks:
            counts[r] = counts.get(r, 0) + 1

        suit_counts: Dict[str, int] = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1

        board_counts: Dict[int, int] = {}
        for r in board_ranks:
            board_counts[r] = board_counts.get(r, 0) + 1

        # Multiples
        max_count = max(counts.values()) if counts else 0
        pairs = [r for r, c in counts.items() if c == 2]
        trips = [r for r, c in counts.items() if c == 3]
        quads = [r for r, c in counts.items() if c == 4]

        # Flush and draw
        flush_suit = None
        is_flush = False
        flush_draw = False
        for s, c in suit_counts.items():
            if c >= 5:
                is_flush = True
                flush_suit = s
                break
            if c == 4:
                flush_draw = True
                flush_suit = s

        # Check if our hole contributes to flush draw
        contributes_flush = (s1 == flush_suit or s2 == flush_suit) if flush_suit else False

        # Straight and straight draw
        unique_ranks = sorted(set(ranks))
        # Ace low handling
        if 14 in unique_ranks:
            unique_ranks = sorted(set(unique_ranks + [1]))
        is_straight = False
        straight_draw = False
        for start in range(1, 11):
            window = set(range(start, start + 5))
            cnt = len(window.intersection(unique_ranks))
            if cnt == 5:
                is_straight = True
                break
            if cnt == 4:
                straight_draw = True

        # Overpair, top pair, middle pair determination
        overpair = False
        top_pair = False
        middle_pair = False
        two_pair = False

        board_max = max(board_ranks) if board_ranks else 0
        has_pair_with_board = False
        # Determine pairs using our hole cards
        # Overpair: pocket pair greater than board highest
        if r1 == r2 and r1 > board_max and len(board_ranks) >= 3:
            overpair = True

        # Determine if we pair the board
        hole_ranks = [r1, r2]
        pair_ranks_ours = [r for r in hole_ranks if board_counts.get(r, 0) >= 1]

        if pair_ranks_ours:
            has_pair_with_board = True
            # If we pair the top board rank
            if board_max in pair_ranks_ours:
                top_pair = True
            else:
                # Middle pair if we pair a non-top rank on the board and not bottom
                if board_ranks:
                    sorted_board = sorted(set(board_ranks))
                    if len(sorted_board) >= 2:
                        if pair_ranks_ours[0] != min(sorted_board) and pair_ranks_ours[0] != max(sorted_board):
                            middle_pair = True
                        else:
                            middle_pair = False
                    else:
                        middle_pair = True  # Board with same ranks; treat as middle-ish
        # Two pair if we connect with two different board ranks or pocket + board pair
        if len(pair_ranks_ours) >= 2:
            two_pair = True
        if (r1 == r2) and board_counts.get(r1, 0) >= 1:
            two_pair = True

        # Full house detection
        full_house = False
        if trips and (pairs or len(trips) >= 2):
            full_house = True
        # Also board combos with our pair contributing
        if (r1 == r2 and r1 in board_counts and board_counts[r1] >= 2) or (trips and has_pair_with_board):
            full_house = True

        # Strength assignment by category
        strength = 0.20  # baseline high card
        if quads:
            strength = 0.98
        elif full_house:
            strength = 0.94
        elif is_flush:
            strength = 0.90
        elif is_straight:
            strength = 0.86
        elif trips:
            # Trips using hole vs only on board
            if r1 in trips or r2 in trips:
                strength = 0.82
            else:
                strength = 0.78
        elif two_pair:
            strength = 0.72
        elif overpair:
            strength = 0.70
        elif top_pair:
            # Kicker matters
            kicker = r1 if r2 == board_max else (r2 if r1 == board_max else max(r1, r2))
            if kicker >= 13:
                strength = 0.66
            elif kicker >= 11:
                strength = 0.62
            else:
                strength = 0.58
        elif middle_pair or has_pair_with_board:
            strength = 0.52
        else:
            # Draws
            if flush_draw and contributes_flush:
                if straight_draw:
                    strength = 0.56  # combo draw
                else:
                    strength = 0.52
            elif straight_draw:
                strength = 0.50
            else:
                # Overcards: 2 overcards to board on flop carry some equity
                if len(board_ranks) >= 3:
                    board_hi = max(board_ranks)
                    if r1 > board_hi and r2 > board_hi:
                        strength = 0.42
                    elif r1 > board_hi or r2 > board_hi:
                        strength = 0.36
                    else:
                        strength = 0.22
                else:
                    strength = 0.25

        # Multi-way penalty and street-specific adjustment
        if num_players >= 4:
            strength -= min(0.12, 0.03 * (num_players - 3))
        elif num_players == 3:
            strength -= 0.02

        # On river, draws are worthless -> reduce non-made hand strength
        if street_l == "river":
            if strength < 0.55:
                strength *= 0.85

        # Clamp strength
        strength = max(0.0, min(1.0, strength))
        return float(strength)