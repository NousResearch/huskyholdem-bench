from typing import List, Tuple, Optional, Dict
import random

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


RANK_ORDER = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
              '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}


def card_rank(card: str) -> int:
    # card like 'Ah' or 'Td'
    if not card or len(card) < 2:
        return 0
    return RANK_ORDER.get(card[0].upper(), 0)


def card_suit(card: str) -> str:
    if not card or len(card) < 2:
        return ''
    return card[1].lower()


def sort_ranks_desc(ranks: List[int]) -> List[int]:
    return sorted(ranks, reverse=True)


def has_straight(ranks: List[int]) -> bool:
    # ranks may contain duplicates; treat Ace as both high and low
    if not ranks:
        return False
    unique = sorted(set(ranks))
    if 14 in unique:
        unique.append(1)  # Ace low
    # scan sequences
    streak = 1
    for i in range(1, len(unique)):
        if unique[i] == unique[i - 1] + 1:
            streak += 1
            if streak >= 5:
                return True
        else:
            streak = 1
    return False


def straight_draw_strength(ranks: List[int]) -> float:
    # Naive draw detection: open-ender ~0.17, gutshot ~0.1 (approximate equities)
    # We'll look for sequences of 4 within unique ranks (+ ace-low)
    if not ranks:
        return 0.0
    unique = sorted(set(ranks))
    if 14 in unique:
        unique.append(1)
    # Find longest streak lengths and gaps of 1 in 5-window
    best = 0.0
    for start_idx in range(len(unique)):
        count = 1
        last = unique[start_idx]
        gaps = 0
        for j in range(start_idx + 1, len(unique)):
            if unique[j] == last:
                continue
            if unique[j] == last + 1:
                count += 1
            else:
                gaps += (unique[j] - last - 1)
                count += 1
            last = unique[j]
            if count >= 4:
                # Approximate: if gaps==0 within 4-length -> open-ender
                if gaps == 0:
                    best = max(best, 0.17)
                elif gaps == 1:
                    best = max(best, 0.10)
                # we don't break to see if a better draw appears
            if count >= 5:
                break
    return best


class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips: int = 0
        self.blind_amount: int = 0  # assume small blind by default
        self.big_blind_player_id: Optional[int] = None
        self.small_blind_player_id: Optional[int] = None
        self.all_players: List[int] = []
        self.hand_round_num: Optional[int] = None
        self.hole_cards: Optional[List[str]] = None
        self.preflop_raiser: bool = False
        self.last_action: Optional[PokerAction] = None
        self.rng = random.Random(42)
        self.big_blind_amount: int = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int,
                 big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        # Initialize match info
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount if blind_amount is not None else 0
        self.big_blind_amount = self.blind_amount * 2 if self.blind_amount else 0
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = list(all_players) if all_players else []
        # Try to capture initial hand if provided (may vary per framework; guard for safety)
        self.hole_cards = list(player_hands)[:2] if player_hands and len(player_hands) >= 2 else None
        self.hand_round_num = None
        self.preflop_raiser = False
        self.last_action = None

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # New hand starting preflop; reset state
        self.hand_round_num = round_state.round_num
        # Attempt to extract hole cards from round_state if framework provides them
        self.hole_cards = self._extract_hole_cards(round_state)
        self.preflop_raiser = False
        self.last_action = None
        # Blind amounts may change with blinds increase; infer from min_raise if possible
        try:
            if round_state.min_raise and round_state.min_raise > 0:
                # Many engines set min_raise equal to big blind preflop when no bet has been made
                # Do not override if already set; just update heuristic big blind amount conservatively
                self.big_blind_amount = max(self.big_blind_amount, round_state.min_raise)
        except Exception:
            pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """
        try:
            # Keep hole cards updated if provided later
            if self.hand_round_num != round_state.round_num:
                # New hand started without on_round_start? Reset
                self.on_round_start(round_state, remaining_chips)

            my_id_str = str(self.id)
            my_bet = int(round_state.player_bets.get(my_id_str, 0)) if round_state.player_bets else 0
            current_bet = int(round_state.current_bet) if round_state.current_bet is not None else 0
            to_call = max(0, current_bet - my_bet)
            can_check = (to_call == 0)
            min_raise = int(round_state.min_raise) if round_state.min_raise is not None else 0
            max_raise = max(0, int(round_state.max_raise) if round_state.max_raise is not None else 0)
            pot = int(round_state.pot) if round_state.pot is not None else 0
            community = list(round_state.community_cards) if round_state.community_cards else []
            stage = (round_state.round or '').lower()  # 'Preflop','Flop','Turn','River'

            # Active players estimation
            active_players_count = self._estimate_active_players(round_state)

            # Attempt to extract hole cards if not known
            if self.hole_cards is None:
                self.hole_cards = self._extract_hole_cards(round_state)

            # Preflop strategy
            if stage.startswith('pre'):
                strength = self._preflop_strength(self.hole_cards) if self.hole_cards else 0.5
                # Adjust strength a bit for table size (stronger HU, weaker multiway)
                if active_players_count <= 2:
                    strength += 0.02
                else:
                    strength -= min(0.04, (active_players_count - 2) * 0.01)
                strength = max(0.0, min(1.0, strength))

                # Preflop raise sizing heuristic
                open_size = int(max(min_raise, self.big_blind_amount * 2.5)) if self.big_blind_amount > 0 else min_raise
                three_bet_size = int(max(min_raise, to_call * 3))

                if can_check:
                    # Opportunity to open the pot
                    if self._can_raise(min_raise, max_raise) and strength >= 0.62:
                        amount = self._clamp_raise(open_size, min_raise, max_raise)
                        self.preflop_raiser = True
                        self.last_action = PokerAction.RAISE
                        return PokerAction.RAISE, amount
                    else:
                        self.last_action = PokerAction.CHECK
                        return PokerAction.CHECK, 0
                else:
                    # Facing a bet
                    # Pot odds
                    pot_odds = to_call / (pot + to_call + 1e-9)
                    # Decide actions based on strength and cost
                    # Strong hands can 3-bet
                    if strength >= 0.75 and self._can_raise(min_raise, max_raise):
                        amount = self._clamp_raise(three_bet_size, min_raise, max_raise)
                        # If our desired raise equals max, consider all-in only if it equals our stack
                        if amount >= max_raise and remaining_chips <= max_raise + 1:
                            self.last_action = PokerAction.ALL_IN
                            return PokerAction.ALL_IN, 0
                        self.preflop_raiser = True
                        self.last_action = PokerAction.RAISE
                        return PokerAction.RAISE, amount
                    # Medium strength: call if affordable
                    call_threshold = 0.50 if to_call <= self.big_blind_amount * 2 else 0.57
                    if strength >= call_threshold and pot_odds <= 0.45:
                        self.last_action = PokerAction.CALL
                        return PokerAction.CALL, 0
                    # Cheap defend in big blind
                    if to_call <= max(self.big_blind_amount, min_raise) and strength >= 0.48:
                        self.last_action = PokerAction.CALL
                        return PokerAction.CALL, 0
                    # Otherwise fold
                    self.last_action = PokerAction.FOLD
                    return PokerAction.FOLD, 0

            # Postflop strategy
            # Estimate hand strength and draw strength
            strength, draw_eq = self._postflop_strength(self.hole_cards, community)
            # Adjust for heads-up slightly
            if active_players_count <= 2:
                strength += 0.01
            else:
                strength -= min(0.03, (active_players_count - 2) * 0.005)
            strength = max(0.0, min(1.0, strength))

            # Determine if we want to bet/raise
            # Value thresholds
            very_strong = strength >= 0.82
            strong = strength >= 0.68
            medium = strength >= 0.58
            weak = strength < 0.45

            # Compute pot odds when facing a bet
            if not can_check:
                pot_odds = to_call / (pot + to_call + 1e-9)
                # If very strong: raise for value
                if very_strong and self._can_raise(min_raise, max_raise):
                    # Typical raise: 3x the bet or ~60% pot
                    desired = max(int(to_call * 3), int(pot * 0.6))
                    amount = self._clamp_raise(desired, min_raise, max_raise)
                    # Consider jamming if short or amount equals max
                    if amount >= max_raise and remaining_chips <= max_raise + 1:
                        self.last_action = PokerAction.ALL_IN
                        return PokerAction.ALL_IN, 0
                    self.last_action = PokerAction.RAISE
                    return PokerAction.RAISE, amount
                # Strong hands: mostly call, sometimes raise small
                if strong:
                    # If bet is small relative to pot, call; otherwise call if pot odds ok
                    if pot_odds <= 0.45 or to_call <= max(min_raise, self.big_blind_amount * 2):
                        self.last_action = PokerAction.CALL
                        return PokerAction.CALL, 0
                    else:
                        # Too expensive without nutted strength
                        self.last_action = PokerAction.FOLD
                        return PokerAction.FOLD, 0
                # Draw-based decisions
                if draw_eq > 0.0:
                    # Effective equity is draw_eq; call if pot odds justify
                    # Add a small bluff equity buffer
                    if draw_eq + 0.03 >= pot_odds:
                        self.last_action = PokerAction.CALL
                        return PokerAction.CALL, 0
                    else:
                        self.last_action = PokerAction.FOLD
                        return PokerAction.FOLD, 0
                # Medium marginal hands: call cheap, fold expensive
                if medium and pot_odds <= 0.35:
                    self.last_action = PokerAction.CALL
                    return PokerAction.CALL, 0
                # Otherwise fold
                self.last_action = PokerAction.FOLD
                return PokerAction.FOLD, 0
            else:
                # We can check or bet
                # Choose bet sizing as a fraction of pot; translate to raise amount
                if very_strong and self._can_raise(min_raise, max_raise):
                    desired = int(max(min_raise, pot * 0.65))
                    amount = self._clamp_raise(desired, min_raise, max_raise)
                    if amount >= max_raise and remaining_chips <= max_raise + 1:
                        self.last_action = PokerAction.ALL_IN
                        return PokerAction.ALL_IN, 0
                    self.last_action = PokerAction.RAISE
                    return PokerAction.RAISE, amount
                # If we were preflop aggressor, consider c-bet with some frequency
                if self.preflop_raiser and self._can_raise(min_raise, max_raise):
                    # Semi-bluff or value bet with medium/strong or draws
                    if strong or (medium and self.rng.random() < 0.5) or (draw_eq >= 0.10 and self.rng.random() < 0.6):
                        desired = int(max(min_raise, pot * 0.5))
                        amount = self._clamp_raise(desired, min_raise, max_raise)
                        self.last_action = PokerAction.RAISE
                        return PokerAction.RAISE, amount
                # Otherwise check
                self.last_action = PokerAction.CHECK
                return PokerAction.CHECK, 0

        except Exception:
            # Fail-safe: never crash; choose a safe action
            try:
                # Try to determine if we can check
                my_id_str = str(self.id)
                my_bet = int(round_state.player_bets.get(my_id_str, 0)) if round_state.player_bets else 0
                current_bet = int(round_state.current_bet) if round_state.current_bet is not None else 0
                to_call = max(0, current_bet - my_bet)
                if to_call == 0:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0
            except Exception:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        # Reset per-hand states
        self.hole_cards = None
        self.hand_round_num = None
        self.preflop_raiser = False
        self.last_action = None

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Nothing special; keep stable and lightweight
        pass

    # ---------------- Helper methods ----------------

    def _extract_hole_cards(self, round_state: RoundStateClient) -> Optional[List[str]]:
        # Try various possible fields that may exist in different frameworks
        try_fields = [
            'hole_cards', 'hand', 'cards', 'private_cards', 'player_hands', 'my_cards'
        ]
        for field in try_fields:
            if hasattr(round_state, field):
                val = getattr(round_state, field)
                if isinstance(val, list) and len(val) >= 2 and isinstance(val[0], str):
                    return val[:2]
                if isinstance(val, dict):
                    # Maybe a dict of player_id -> hand
                    my_key = str(self.id)
                    if my_key in val and isinstance(val[my_key], list) and len(val[my_key]) >= 2:
                        return val[my_key][:2]
        return None

    def _estimate_active_players(self, round_state: RoundStateClient) -> int:
        # Estimate active players using player_actions if available; else fall back to all_players length
        try:
            if round_state.player_actions:
                folded = 0
                seen_ids = set()
                for pid_str, act in round_state.player_actions.items():
                    seen_ids.add(pid_str)
                    if isinstance(act, str) and act.lower() == 'fold':
                        folded += 1
                if self.all_players:
                    total = len(self.all_players)
                else:
                    total = len(seen_ids) if seen_ids else 2
                active = max(2, total - folded)
                return active
        except Exception:
            pass
        return max(2, len(self.all_players)) if self.all_players else 2

    def _preflop_strength(self, hole_cards: Optional[List[str]]) -> float:
        if not hole_cards or len(hole_cards) < 2:
            return 0.5
        c1, c2 = hole_cards[0], hole_cards[1]
        r1, r2 = card_rank(c1), card_rank(c2)
        s1, s2 = card_suit(c1), card_suit(c2)
        if r1 < r2:
            r1, r2 = r2, r1  # r1 >= r2

        suited = (s1 == s2)
        gap = abs(r1 - r2) - 1
        pair = (r1 == r2)

        # Base strength
        strength = 0.5
        if pair:
            if r1 >= 14:
                strength = 0.99  # AA
            elif r1 == 13:
                strength = 0.93  # KK
            elif r1 == 12:
                strength = 0.90  # QQ
            elif r1 == 11:
                strength = 0.86  # JJ
            elif r1 == 10:
                strength = 0.82  # TT
            elif r1 == 9:
                strength = 0.76
            elif r1 == 8:
                strength = 0.72
            elif r1 == 7:
                strength = 0.66
            elif r1 == 6:
                strength = 0.60
            elif r1 == 5:
                strength = 0.56
            else:
                strength = 0.52
        else:
            high_combo = (r1 + r2) / 28.0  # normalized high card value
            strength = 0.35 + 0.5 * high_combo
            # Suited bonus
            if suited:
                strength += 0.03
            # Connectivity bonus
            if gap <= 0:
                strength += 0.05
            elif gap == 1:
                strength += 0.03
            elif gap == 2:
                strength += 0.01
            # Both T+ bonus
            if r1 >= 10 and r2 >= 10:
                strength += 0.08
            # Ax suited bonus
            if suited and r1 == 14:
                strength += 0.04

        return max(0.0, min(1.0, strength))

    def _postflop_strength(self, hole_cards: Optional[List[str]], board: List[str]) -> Tuple[float, float]:
        # Returns (strength in [0,1], draw_equity in [0, ~0.2])
        if not board:
            # No board given (shouldn't happen postflop), fallback to preflop
            return (self._preflop_strength(hole_cards) if hole_cards else 0.5, 0.0)

        # If we don't know our cards, be conservative: very weak baseline without hole info
        if not hole_cards or len(hole_cards) < 2:
            ranks = [card_rank(c) for c in board]
            base = 0.4
            # Board-based made hand detect
            counts: Dict[int, int] = {}
            suit_counts: Dict[str, int] = {}
            for c in board:
                r = card_rank(c)
                s = card_suit(c)
                counts[r] = counts.get(r, 0) + 1
                suit_counts[s] = suit_counts.get(s, 0) + 1
            max_count = max(counts.values()) if counts else 1
            flush_board = max(suit_counts.values()) >= 5 if suit_counts else False
            straight_board = has_straight(ranks)

            if max_count >= 4:
                base = 0.9
            elif any(v >= 3 for v in counts.values()) and any(v >= 2 for v in counts.values()):
                base = 0.88
            elif flush_board:
                base = 0.7
            elif straight_board:
                base = 0.65
            elif any(v >= 3 for v in counts.values()):
                base = 0.6
            elif sum(1 for v in counts.values() if v >= 2) >= 2:
                base = 0.55
            elif any(v >= 2 for v in counts.values()):
                base = 0.5
            draw_eq = straight_draw_strength(ranks)
            return max(0.0, min(1.0, base)), max(0.0, min(0.2, draw_eq))

        # Combine hole + board
        cards = hole_cards + board
        ranks = [card_rank(c) for c in cards]
        suits = [card_suit(c) for c in cards]
        board_ranks = [card_rank(c) for c in board]
        board_suits = [card_suit(c) for c in board]
        my_r1, my_r2 = card_rank(hole_cards[0]), card_rank(hole_cards[1])
        my_s1, my_s2 = card_suit(hole_cards[0]), card_suit(hole_cards[1])
        board_max = max(board_ranks) if board_ranks else 0

        counts: Dict[int, int] = {}
        for r in ranks:
            counts[r] = counts.get(r, 0) + 1
        board_counts: Dict[int, int] = {}
        for r in board_ranks:
            board_counts[r] = board_counts.get(r, 0) + 1

        suit_counts: Dict[str, int] = {}
        for s in suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
        board_suit_counts: Dict[str, int] = {}
        for s in board_suits:
            board_suit_counts[s] = board_suit_counts.get(s, 0) + 1

        max_count = max(counts.values()) if counts else 1
        board_max_count = max(board_counts.values()) if board_counts else 1

        # Flush/straight detection
        flush_suit = None
        for s, cnt in suit_counts.items():
            if cnt >= 5:
                flush_suit = s
                break
        board_flush_suit = None
        for s, cnt in board_suit_counts.items():
            if cnt >= 5:
                board_flush_suit = s
                break
        have_flush = flush_suit is not None and (my_s1 == flush_suit or my_s2 == flush_suit)
        board_only_flush = (board_flush_suit is not None) and not have_flush

        straight_present = has_straight(ranks)
        board_straight = has_straight(board_ranks) and not straight_present  # approximate

        # Determine made hand category strength
        strength = 0.4

        # Quads
        if max_count >= 4:
            strength = 0.99
        # Full house
        elif any(v >= 3 for v in counts.values()) and sum(1 for v in counts.values() if v >= 2) >= 2:
            strength = 0.95
        # Flush
        elif have_flush:
            strength = 0.90
        elif board_only_flush:
            strength = 0.70
        # Straight
        elif straight_present:
            strength = 0.85
        elif board_straight:
            strength = 0.65
        # Trips
        elif any(v >= 3 for v in counts.values()):
            # If trips come from board only without our card contributing, it's weaker
            trips_rank = max((r for r, v in counts.items() if v >= 3), default=None)
            board_trips = trips_rank is not None and board_counts.get(trips_rank, 0) >= 3
            if board_trips and my_r1 != trips_rank and my_r2 != trips_rank:
                strength = 0.55
            else:
                strength = 0.80
        # Two pair
        elif sum(1 for v in counts.values() if v >= 2) >= 2:
            # Check if at least one pair uses our hole cards
            uses_hole = (board_counts.get(my_r1, 0) >= 1 or board_counts.get(my_r2, 0) >= 1) or (my_r1 == my_r2)
            if uses_hole:
                strength = 0.75
            else:
                strength = 0.50
        # One pair / overpair / top pair
        elif any(v >= 2 for v in counts.values()):
            # Determine if it's an overpair or top pair
            # Overpair: we hold a pocket pair above all board ranks
            if my_r1 == my_r2 and my_r1 > board_max:
                strength = 0.78
            else:
                # If our pair equals top board rank and our kicker good
                pair_rank = next((r for r, v in counts.items() if v >= 2 and r in (my_r1, my_r2)), None)
                if pair_rank is not None:
                    if pair_rank == board_max:
                        kicker = max(my_r1, my_r2) if (my_r1 != my_r2) else pair_rank
                        kicker_strength = (kicker - 6) / 8.0  # scale from 6..14 -> 0..1
                        strength = 0.60 + 0.05 * max(0.0, min(1.0, kicker_strength))
                    else:
                        # Middle/bottom pair
                        if pair_rank >= 10:
                            strength = 0.56
                        elif pair_rank >= 7:
                            strength = 0.52
                        else:
                            strength = 0.48
                else:
                    strength = 0.45
        else:
            # High card; if we have two overs to board, add a bit
            over1 = my_r1 > board_max
            over2 = my_r2 > board_max
            if over1 and over2:
                strength = 0.46
            elif over1 or over2:
                strength = 0.44
            else:
                strength = 0.35

        # Draw equities
        draw_eq = 0.0
        # Flush draw (4 to a suit) and at least one of our hole cards in that suit
        max_suit = None
        max_suit_count = 0
        for s, cnt in suit_counts.items():
            if cnt > max_suit_count:
                max_suit_count = cnt
                max_suit = s
        if max_suit_count == 4 and (my_s1 == max_suit or my_s2 == max_suit):
            # Prefer nut flush draw (one of our cards is Ace of that suit)
            is_nut_draw = (my_s1 == max_suit and my_r1 == 14) or (my_s2 == max_suit and my_r2 == 14)
            draw_eq += 0.12 if is_nut_draw else 0.10

        # Straight draws
        draw_eq += straight_draw_strength(ranks)

        # Small bonus for two overcards to board (turn+)
        if len(board) >= 3:
            overcards = int(my_r1 > board_max) + int(my_r2 > board_max)
            if overcards >= 2:
                draw_eq += 0.04
            elif overcards == 1:
                draw_eq += 0.02

        draw_eq = max(0.0, min(0.20, draw_eq))
        return max(0.0, min(1.0, strength)), draw_eq

    def _can_raise(self, min_raise: int, max_raise: int) -> bool:
        return min_raise is not None and max_raise is not None and min_raise > 0 and max_raise >= min_raise

    def _clamp_raise(self, desired: int, min_raise: int, max_raise: int) -> int:
        if not self._can_raise(min_raise, max_raise):
            return 0
        return max(min_raise, min(desired, max_raise))