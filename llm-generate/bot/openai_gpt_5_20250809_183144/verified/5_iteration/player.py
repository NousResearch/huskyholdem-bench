from typing import List, Tuple, Dict, Any, Optional
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

# Utility constants
RANK_ORDER = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
              '7': 7, '8': 8, '9': 9, 'T': 10,
              'J': 11, 'Q': 12, 'K': 13, 'A': 14}


class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips: int = 0
        self.remaining_chips: int = 0
        self.hole_cards: List[str] = []
        self.small_blind_amount: int = 0  # Assumed blind_amount is small blind
        self.big_blind_amount: int = 0
        self.big_blind_player_id: Optional[int] = None
        self.small_blind_player_id: Optional[int] = None
        self.all_players: List[int] = []
        self.hand_count: int = 0
        self.round_name: str = ""
        self.last_round_num: int = -1
        self.debug_enabled: bool = False  # Set True for internal debugging prints (avoid in competition)

        # Simple aggressive/defensive tuning parameters
        self.aggression_factor: float = 1.0  # scales bet sizes
        self.value_threshold: float = 0.75
        self.semibluff_threshold: float = 0.23
        self.call_margin: float = 0.08

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int,
                 big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        # Called at the start of each hand (assumption based on competition environment)
        self.starting_chips = starting_chips if self.starting_chips == 0 else self.starting_chips
        self.remaining_chips = starting_chips  # will be updated by framework, but keep a local view
        self.hole_cards = list(player_hands) if player_hands else []
        self.small_blind_amount = int(blind_amount)
        self.big_blind_amount = int(max(2 * self.small_blind_amount, 1))
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = list(all_players) if all_players else []
        self.hand_count += 1
        self.round_name = "Preflop"
        self.last_round_num = -1

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Called at the start of betting round (Preflop/Flop/Turn/River)
        self.remaining_chips = remaining_chips
        self.round_name = round_state.round
        self.last_round_num = round_state.round_num

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """
        try:
            self.remaining_chips = remaining_chips

            # Extract round info safely
            my_id_str = str(self.id) if self.id is not None else ""
            pot = int(round_state.pot) if round_state.pot is not None else 0
            current_bet = int(round_state.current_bet) if round_state.current_bet is not None else 0
            min_raise = int(round_state.min_raise) if round_state.min_raise is not None else 0
            max_raise = int(round_state.max_raise) if round_state.max_raise is not None else 0
            player_bets: Dict[str, int] = round_state.player_bets or {}
            my_bet = int(player_bets.get(my_id_str, 0))
            to_call = max(0, current_bet - my_bet)
            community_cards = round_state.community_cards or []
            n_active = len(round_state.current_player or [])

            # Safety: if we cannot afford anything and there's nothing to call, check
            if remaining_chips <= 0 and to_call == 0:
                return PokerAction.CHECK, 0
            if remaining_chips <= 0 and to_call > 0:
                # We're effectively all-in or cannot act, try CALL (engine should treat as all-in call)
                return PokerAction.CALL, 0

            # Decide based on street
            street = (round_state.round or "").lower()
            if street == "preflop":
                return self._act_preflop(round_state, to_call, pot, min_raise, max_raise, n_active)
            else:
                return self._act_postflop(round_state, to_call, pot, min_raise, max_raise, community_cards, n_active)
        except Exception:
            # Failsafe: choose safe minimal EV-losing action
            # If can check, then check; else call small; else fold
            try:
                my_id_str = str(self.id) if self.id is not None else ""
                current_bet = int(round_state.current_bet) if round_state.current_bet is not None else 0
                player_bets: Dict[str, int] = round_state.player_bets or {}
                my_bet = int(player_bets.get(my_id_str, 0))
                to_call = max(0, current_bet - my_bet)
                if to_call == 0:
                    return PokerAction.CHECK, 0
                if to_call <= max(1, self.big_blind_amount):
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
            except Exception:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        self.remaining_chips = remaining_chips

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Could adjust aggression based on results, keep it simple/stable
        pass

    # ------------------------
    # Strategy helper methods
    # ------------------------

    def _act_preflop(self, round_state: RoundStateClient, to_call: int, pot: int,
                     min_raise: int, max_raise: int, n_active: int) -> Tuple[PokerAction, int]:
        # Calculate simple preflop strength
        s = self._preflop_strength(self.hole_cards)
        bb = max(self.big_blind_amount, 1)
        sb = max(self.small_blind_amount, 1)

        my_id = self.id
        is_sb = (my_id == self.small_blind_player_id)
        is_bb = (my_id == self.big_blind_player_id)

        # Heads-up adjustments
        hu = (len(self.all_players) == 2 or n_active == 2)

        # Facing action or opening?
        # In preflop, current_bet is typically BB. If SB to act and to_call == (BB - SB), it's unopened pot.
        # If to_call == 0 for BB, it's an option to check; else facing raise size.
        current_bet = round_state.current_bet
        my_bet = (round_state.player_bets or {}).get(str(self.id), 0)
        my_bet = int(my_bet or 0)

        # Determine whether pot has been raised beyond blinds
        pot_raised = current_bet > bb

        # Define opening and 3bet targets
        def clamp_raise(target_total: int) -> Optional[int]:
            # Ensure valid raise "to" amount
            if max_raise <= 0:
                return None
            target = max(min_raise, target_total)
            target = min(target, max_raise)
            if target <= current_bet:
                # If cannot exceed current bet, raising is not allowed
                if max_raise > current_bet:
                    target = max(current_bet + 1, min_raise)
                else:
                    return None
            return int(max(target, 1))

        # SB opening strategy (HU or 6-max)
        if is_sb:
            # Unopened pot if not raised beyond BB
            if not pot_raised:
                # SB acts first: to_call == BB - SB
                if s >= 0.60:
                    # Strong hand: open to 3x BB
                    raise_to = clamp_raise(int(3.0 * bb))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                if s >= 0.40:
                    # Medium: open to 2.5x BB
                    raise_to = clamp_raise(int(2.5 * bb))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                # Weak: complete if cheap, else fold
                if to_call <= sb:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
            else:
                # Facing a raise after we posted SB (opponent 3-bet unlikely in HU preflop flow, but be robust)
                # Tighten thresholds relative to raise size (to_call measures incremental from our current bet)
                if to_call <= 2 * bb:
                    if s >= 0.65:
                        # 3-bet to ~3x current bet
                        raise_to = clamp_raise(int(3.0 * current_bet))
                        if raise_to:
                            return PokerAction.RAISE, raise_to
                        return PokerAction.CALL, 0
                    if s >= 0.35:
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0
                else:
                    if s >= 0.72:
                        raise_to = clamp_raise(int(2.5 * current_bet))
                        if raise_to:
                            return PokerAction.RAISE, raise_to
                        return PokerAction.CALL, 0
                    if s >= 0.52:
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0

        # BB strategy
        if is_bb:
            # If no raise and to_call == 0, we can check or raise
            if to_call == 0 and not pot_raised:
                # Option to check; raise some decent hands
                if s >= 0.65:
                    raise_to = clamp_raise(int(3.0 * bb))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                if s >= 0.45:
                    raise_to = clamp_raise(int(2.5 * bb))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                return PokerAction.CHECK, 0
            else:
                # Facing SB open (or bigger)
                if to_call <= 2 * bb:
                    if s >= 0.68:
                        raise_to = clamp_raise(int(3.0 * current_bet))
                        if raise_to:
                            return PokerAction.RAISE, raise_to
                        return PokerAction.CALL, 0
                    if s >= 0.36:
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0
                elif to_call <= 4 * bb:
                    if s >= 0.55:
                        return PokerAction.CALL, 0
                    if s >= 0.73:
                        raise_to = clamp_raise(int(2.5 * current_bet))
                        if raise_to:
                            return PokerAction.RAISE, raise_to
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0
                else:
                    # Large raise (or shove)
                    if s >= 0.80:
                        # Call or shove depending on stack (prefer call to avoid invalid raise bounds)
                        if to_call >= self.remaining_chips:
                            return PokerAction.CALL, 0
                        raise_to = clamp_raise(max_raise)
                        if raise_to:
                            return PokerAction.RAISE, raise_to
                        return PokerAction.CALL, 0
                    if s >= 0.62:
                        return PokerAction.CALL, 0
                    return PokerAction.FOLD, 0

        # For other positions (multiway), play tighter: open-raise strong, call medium with good price, fold weak
        if not pot_raised and to_call <= max(bb, 2 * sb):
            if s >= 0.62:
                raise_to = clamp_raise(int(2.5 * bb))
                if raise_to:
                    return PokerAction.RAISE, raise_to
            if s >= 0.45:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0
        else:
            # Facing raise multiway: tighten further
            if to_call <= 2 * bb:
                if s >= 0.68:
                    raise_to = clamp_raise(int(3.0 * current_bet))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                    return PokerAction.CALL, 0
                if s >= 0.48:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
            else:
                if s >= 0.78:
                    raise_to = clamp_raise(int(2.5 * current_bet))
                    if raise_to:
                        return PokerAction.RAISE, raise_to
                    return PokerAction.CALL, 0
                if s >= 0.60:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0

    def _act_postflop(self, round_state: RoundStateClient, to_call: int, pot: int,
                       min_raise: int, max_raise: int, community_cards: List[str], n_active: int) -> Tuple[PokerAction, int]:
        # Evaluate hand strength and draws
        eval_info = self._evaluate_hand(community_cards, self.hole_cards)
        hs = eval_info.get('strength', 0.1)
        strong_draw = eval_info.get('strong_draw', False)
        draw_score = eval_info.get('draw_score', 0.0)
        category_rank = eval_info.get('category_rank', 0)

        current_bet = int(round_state.current_bet or 0)
        my_bet = int((round_state.player_bets or {}).get(str(self.id), 0) or 0)
        to_call = max(0, current_bet - my_bet)

        def clamp_raise(target_total: int) -> Optional[int]:
            if max_raise <= 0:
                return None
            target = max(min_raise, target_total)
            target = min(target, max_raise)
            if target <= current_bet:
                if max_raise > current_bet:
                    target = max(current_bet + 1, min_raise)
                else:
                    return None
            return int(max(target, 1))

        # If no bet to us, consider betting or checking
        if to_call == 0:
            # Value bet strong hands
            if hs >= max(self.value_threshold, 0.75):
                # Bet ~70% pot
                bet_size = int(max(min_raise, int(0.7 * pot * self.aggression_factor)))
                bet_to = clamp_raise(bet_size)
                if bet_to:
                    return PokerAction.RAISE, bet_to
                return PokerAction.CHECK, 0
            # Semi-bluff with decent draws
            if strong_draw or draw_score >= self.semibluff_threshold:
                bet_size = int(max(min_raise, int(0.55 * pot * self.aggression_factor)))
                bet_to = clamp_raise(bet_size)
                if bet_to:
                    return PokerAction.RAISE, bet_to
                return PokerAction.CHECK, 0
            # Occasionally probe with middle pair/top pair weak kicker
            if 0.50 <= hs < 0.75:
                # Small value/protection bet ~40% pot
                bet_size = int(max(min_raise, int(0.4 * pot)))
                bet_to = clamp_raise(bet_size)
                if bet_to:
                    return PokerAction.RAISE, bet_to
            return PokerAction.CHECK, 0

        # Facing a bet: compute pot odds
        denom = float(pot + to_call) + 1e-9
        pot_odds = float(to_call) / denom

        # Very strong: raise for value
        if hs >= 0.85 or category_rank >= 6:
            # Raise to ~2.5x current bet
            raise_to = clamp_raise(int(current_bet * 2.5))
            if raise_to:
                return PokerAction.RAISE, raise_to
            # If can't raise, call
            return PokerAction.CALL, 0

        # Good made hand: often call; raise sometimes
        if hs >= 0.65:
            # If bet is small, raise; else call
            if to_call <= max(1, int(0.3 * pot)):
                raise_to = clamp_raise(int(current_bet * 2.2))
                if raise_to:
                    return PokerAction.RAISE, raise_to
            return PokerAction.CALL, 0

        # Draws: call if pot odds allow, occasional semi-bluff
        if strong_draw or draw_score >= self.semibluff_threshold:
            # Estimate equity for draw
            approx_equity = max(0.22, draw_score)  # FD/OESD ~22-35%
            # If equity beats pot odds (with small margin), call
            if approx_equity >= (pot_odds + self.call_margin * 0.5):
                return PokerAction.CALL, 0
            # Else semi-bluff raise when bet is small to medium
            if to_call <= max(1, int(0.35 * pot)):
                raise_to = clamp_raise(int(current_bet * 2.2))
                if raise_to:
                    return PokerAction.RAISE, raise_to
            # If too expensive, fold
            if to_call > self.remaining_chips:
                return PokerAction.FOLD, 0
            # Default to call rather than spew
            return PokerAction.CALL, 0 if approx_equity >= (pot_odds + self.call_margin) else PokerAction.FOLD, 0

        # Marginal made hands: compare hs to pot odds
        if hs >= max(pot_odds + self.call_margin, 0.28):
            return PokerAction.CALL, 0

        # Otherwise fold
        return PokerAction.FOLD, 0

    # ------------------------
    # Hand evaluation helpers
    # ------------------------

    def _card_rank(self, c: str) -> int:
        if not c or len(c) < 1:
            return 0
        return RANK_ORDER.get(c[0].upper(), 0)

    def _card_suit(self, c: str) -> str:
        if not c or len(c) < 2:
            return ''
        return c[1].lower()

    def _preflop_strength(self, cards: List[str]) -> float:
        # Approximate preflop strength in [0,1]
        if not cards or len(cards) != 2:
            return 0.0
        r1 = self._card_rank(cards[0])
        r2 = self._card_rank(cards[1])
        s1 = self._card_suit(cards[0])
        s2 = self._card_suit(cards[1])
        hi = max(r1, r2)
        lo = min(r1, r2)
        suited = (s1 == s2)
        gap = abs(r1 - r2) - 1

        # Base from high cards
        base = (hi * 0.60 + lo * 0.25) / 14.0

        # Pair bonus
        if r1 == r2:
            base = 0.50 + (hi / 14.0) * 0.50  # pairs from 0.5 to 1.0
        else:
            # Suited bonus
            if suited:
                base += 0.04
            # Connectivity bonus
            if gap <= 0:
                base += 0.05
            elif gap == 1:
                base += 0.035
            elif gap == 2:
                base += 0.02
            # Ace-x suited kicker
            if hi == 14 and suited and lo >= 5:
                base += 0.03

        # Penalty for very low junk
        if hi <= 7 and lo <= 6 and not suited and gap >= 3:
            base -= 0.07

        # Clamp
        base = max(0.0, min(1.0, base))
        return float(base)

    def _evaluate_hand(self, board: List[str], hole: List[str]) -> Dict[str, Any]:
        # Returns dict with keys: strength [0,1], category_rank int, strong_draw bool, draw_score float
        cards = list(board) + list(hole)
        ranks = [self._card_rank(c) for c in cards if c]
        suits = [self._card_suit(c) for c in cards if c]
        board_ranks = [self._card_rank(c) for c in board if c]
        board_suits = [self._card_suit(c) for c in board if c]
        hole_ranks = [self._card_rank(c) for c in hole if c]
        hole_suits = [self._card_suit(c) for c in hole if c]

        # Counters
        rank_counts: Dict[int, int] = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        board_rank_counts: Dict[int, int] = {}
        for r in board_ranks:
            board_rank_counts[r] = board_rank_counts.get(r, 0) + 1
        suit_counts: Dict[str, int] = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        board_suit_counts: Dict[str, int] = {}
        for s in board_suits:
            board_suit_counts[s] = board_suit_counts.get(s, 0) + 1

        max_board_rank = max(board_ranks) if board_ranks else 0

        # Flush / Flush draw
        has_flush = False
        flush_suit = ''
        for s, cnt in suit_counts.items():
            if cnt >= 5:
                has_flush = True
                flush_suit = s
                break
        flush_draw = False
        for s, cnt in suit_counts.items():
            if cnt == 4 and s in hole_suits:
                flush_draw = True
                break

        # Straight and straight draws
        straight, oesd, gutshot = self._straight_and_draws(board_ranks, hole_ranks)

        # Sets and pairs
        counts = sorted(rank_counts.values(), reverse=True)
        has_quads = 4 in counts
        has_trips = 3 in counts
        pairs = sum(1 for v in rank_counts.values() if v >= 2)
        has_fullhouse = has_trips and pairs >= 2  # pair count includes the trips' rank counted as pair as well

        # Detailed pair evaluation
        our_pair = False
        overpair = False
        top_pair = False
        middle_pair = False
        weak_pair = False
        if len(hole_ranks) == 2:
            if hole_ranks[0] == hole_ranks[1]:
                our_pair = True
                if max_board_rank and min(hole_ranks) > max_board_rank:
                    overpair = True
            # Pair with board
            for hr in hole_ranks:
                if board_rank_counts.get(hr, 0) >= 1:
                    our_pair = True
                    if hr == max_board_rank:
                        top_pair = True
                    elif max_board_rank and hr < max_board_rank:
                        # Determine middle vs weak based on proximity
                        if hr >= max_board_rank - 2:
                            middle_pair = True
                        else:
                            weak_pair = True

        # Category ranking (8 best -> 0 high card)
        # 8: Straight Flush, 7: Quads, 6: Full House, 5: Flush, 4: Straight, 3: Trips, 2: Two Pair, 1: One Pair, 0: High Card
        category_rank = 0
        if has_quads:
            category_rank = 7
        elif has_fullhouse:
            category_rank = 6
        elif has_flush and straight:
            category_rank = 8
        elif has_flush:
            category_rank = 5
        elif straight:
            category_rank = 4
        elif has_trips:
            category_rank = 3
        elif pairs >= 2:
            category_rank = 2
        elif our_pair or pairs >= 1:
            category_rank = 1
        else:
            category_rank = 0

        # Strength mapping
        strength = 0.10
        if category_rank >= 8:
            strength = 0.98
        elif category_rank == 7:
            strength = 0.94
        elif category_rank == 6:
            strength = 0.90
        elif category_rank == 5:
            strength = 0.82
        elif category_rank == 4:
            strength = 0.78
        elif category_rank == 3:
            # Trips: better if with our card, slightly worse if only on board
            strength = 0.72 if our_pair else 0.68
        elif category_rank == 2:
            strength = 0.62
        elif category_rank == 1:
            # One pair granularity
            if overpair:
                strength = 0.62
            elif top_pair:
                strength = 0.58
            elif middle_pair:
                strength = 0.50
            elif weak_pair or our_pair:
                strength = 0.42
            else:
                strength = 0.38
        else:
            # High card: consider overcards
            if len(hole_ranks) == 2 and board_ranks:
                if max(hole_ranks) > max_board_rank and min(hole_ranks) > max_board_rank - 2:
                    strength = 0.20
                else:
                    strength = 0.12
            else:
                strength = 0.12

        # Draw score
        draw_score = 0.0
        if flush_draw:
            draw_score += 0.24
        if oesd:
            draw_score += 0.24
        if gutshot and not oesd:
            draw_score += 0.12
        strong_draw = (draw_score >= 0.22) or (flush_draw and oesd)

        # If board is very coordinated and our made hand is weak, reduce strength slightly
        if category_rank <= 1 and (flush_draw or oesd or gutshot):
            strength = max(0.0, strength - 0.03)

        return {
            "strength": float(max(0.0, min(1.0, strength))),
            "category_rank": int(category_rank),
            "strong_draw": bool(strong_draw),
            "draw_score": float(draw_score)
        }

    def _straight_and_draws(self, board_ranks: List[int], hole_ranks: List[int]) -> Tuple[bool, bool, bool]:
        # Build rank presence with A low option
        all_ranks = list(set((board_ranks or []) + (hole_ranks or [])))
        board_set = set(board_ranks or [])
        all_set = set(all_ranks)

        # Consider Ace as 1 as well
        def add_wheel(s: set) -> set:
            s2 = set(s)
            if 14 in s2:
                s2.add(1)
            return s2

        all_set_w = add_wheel(all_set)
        board_set_w = add_wheel(board_set)

        # Check straight in combined
        straight = False
        for start in range(1, 11):  # 1..10 inclusive (A-low straight up to 10-J-Q-K-A)
            window = {start, start + 1, start + 2, start + 3, start + 4}
            if window.issubset(all_set_w):
                straight = True
                break

        # Draw detection: count windows with 4 of 5 present post hole add, and compare to board-only
        oesd = False
        gutshot = False
        for start in range(1, 11):
            window = {start, start + 1, start + 2, start + 3, start + 4}
            count_all = len(all_set_w.intersection(window))
            count_board = len(board_set_w.intersection(window))
            if count_all >= 4 and count_board < 4:
                # We contribute to the draw
                # Distinguish OESD vs gutshot: OESD implies 4 consecutive numbers
                # Check if there is a 4-run inside the window
                seq = [start, start + 1, start + 2, start + 3, start + 4]
                present = [x in all_set_w for x in seq]
                # Count maximum consecutive trues
                max_run = 0
                run = 0
                for p in present:
                    if p:
                        run += 1
                        max_run = max(max_run, run)
                    else:
                        run = 0
                if max_run >= 4:
                    oesd = True
                else:
                    gutshot = True

        return straight, oesd, gutshot