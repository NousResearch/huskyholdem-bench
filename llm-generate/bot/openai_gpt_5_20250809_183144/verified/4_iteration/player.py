import random
from typing import List, Tuple, Dict, Any, Optional

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient


class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        # Configuration parameters
        self.starting_chips: int = 0
        self.blind_amount: int = 0  # small blind (assumed)
        self.big_blind_player_id: Optional[int] = None
        self.small_blind_player_id: Optional[int] = None
        self.all_players: List[int] = []

        # Per-hand state
        self.was_raiser_preflop: bool = False
        self.hole_cards: List[str] = []  # if provided by the engine

        # Session tracking
        self.hands_played: int = 0
        self.total_profit: int = 0

        # RNG for mixed strategies
        self.rng = random.Random(17)

    def on_start(
        self,
        starting_chips: int,
        player_hands: List[str],
        blind_amount: int,
        big_blind_player_id: int,
        small_blind_player_id: int,
        all_players: List[int]
    ):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount or 1
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = list(all_players) if all_players is not None else []

        # If engine provides initial hole cards, store them; otherwise keep empty safely
        self.hole_cards = list(player_hands) if player_hands else []

        # Seed RNG deterministically by player id for reproducibility
        try:
            if self.id is not None:
                self.rng.seed(self.id)
        except Exception:
            # Fallback to default seed
            pass

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Reset per-round flags
        self.was_raiser_preflop = False
        # Try to infer blinds dynamically if possible (in case of blind increase)
        try:
            # If preflop and current_bet == 0, min_raise is often big blind value.
            # Update blind if the min_raise looks reasonable.
            if str(round_state.round).lower().startswith('pre'):
                if round_state.min_raise and round_state.min_raise > 0:
                    # Big blind approximated by min_raise at unopened pot
                    # We keep small blind as max(1, big blind // 2) for sizing heuristics
                    # but we only store small blind; big blind inferred as 2*blind_amount
                    self.blind_amount = max(1, round_state.min_raise // 2)
        except Exception:
            pass

        # If engine passes our cards in some form per round, we would update here.
        # Since interface does not specify, we keep stored hole_cards as given (may be empty).

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Core decision logic with robust guards against invalid actions.
        try:
            my_id_str = str(self.id)
            me_bet = int(round_state.player_bets.get(my_id_str, 0)) if round_state.player_bets else 0
            current_bet = int(round_state.current_bet or 0)
            pot = int(round_state.pot or 0)
            min_raise = int(round_state.min_raise or 0)
            max_raise = int(round_state.max_raise or 0)
            eps = 1e-9

            amount_to_call = max(0, current_bet - me_bet)

            # Determine phase
            street_name = str(round_state.round or "").lower()
            is_preflop = 'pre' in street_name
            is_flop = 'flop' in street_name
            is_turn = 'turn' in street_name
            is_river = 'river' in street_name

            # Count active players if possible
            active_player_count = self._estimate_active_players(round_state)

            # Pot odds for calls
            call_pot_odds = amount_to_call / max(1.0, pot + amount_to_call + eps)

            # Strategy thresholds
            # Heads-up we open a lot, multiway we tighten
            if active_player_count <= 2:
                open_raise_freq = 0.70
                cbet_freq = 0.60
                stab_freq = 0.25
                call_small_bet_thresh = 0.30  # fraction of pot
            else:
                open_raise_freq = 0.25
                cbet_freq = 0.45
                stab_freq = 0.15
                call_small_bet_thresh = 0.25

            # Sizing helpers
            # Default raise_by minimal to ensure validity and reduce risk of invalid raise sizes
            def choose_raise_by(target_fraction_of_pot: float, min_bb_multiple: float = 2.5) -> Optional[int]:
                # Compute a target size in chips for raise_by. It must be in [min_raise, max_raise].
                # When unopened (amount_to_call == 0), min_raise is usually big blind.
                # We try to size either by pot faction or blind multiple; default fallback to min_raise.
                target_by_pot = int(max(1, target_fraction_of_pot * max(pot, 1)))
                target_by_bb = int(max(1, min_bb_multiple * max(self.blind_amount, 1)))
                desired = max(target_by_pot, target_by_bb, min_raise)

                # Ensure validity bounds
                if max_raise < 1:
                    return None
                desired = min(desired, max_raise)
                desired = max(desired, min_raise)
                if desired < min_raise or desired > max_raise:
                    return None
                return desired

            # Decide action
            if amount_to_call == 0:
                # We may CHECK or RAISE
                if is_preflop:
                    # Open-raise mix
                    if self.rng.random() < open_raise_freq and min_raise > 0 and max_raise >= min_raise:
                        # Prefer a 2.5bb-3bb open
                        raise_by = choose_raise_by(target_fraction_of_pot=0.0, min_bb_multiple=2.5 + self.rng.random() * 0.7)
                        if raise_by is None:
                            return PokerAction.CHECK, 0
                        self.was_raiser_preflop = True
                        return PokerAction.RAISE, int(raise_by)
                    else:
                        return PokerAction.CHECK, 0
                else:
                    # Post-flop: if we were the preflop raiser, c-bet with some frequency
                    if self.was_raiser_preflop and (is_flop or is_turn) and min_raise > 0 and max_raise >= min_raise:
                        if self.rng.random() < cbet_freq:
                            # C-bet about 50-70% pot as raise_by (model as raise increment)
                            frac = 0.5 + 0.2 * self.rng.random()
                            raise_by = choose_raise_by(target_fraction_of_pot=frac)
                            if raise_by is not None:
                                return PokerAction.RAISE, int(raise_by)
                    # If checked to us and no prior raise, occasionally stab
                    if (is_flop or is_turn) and self.rng.random() < stab_freq and min_raise > 0 and max_raise >= min_raise:
                        frac = 0.4 + 0.2 * self.rng.random()
                        raise_by = choose_raise_by(target_fraction_of_pot=frac)
                        if raise_by is not None:
                            return PokerAction.RAISE, int(raise_by)
                    # Otherwise check back
                    return PokerAction.CHECK, 0
            else:
                # We face a bet; options: CALL/RAISE/FOLD
                # Heuristic: Small bets -> call more; large bets -> fold; occasionally bluff-raise small bets
                bet_fraction_of_pot = amount_to_call / max(1.0, pot + eps)

                # Preflop defense
                if is_preflop:
                    # If small raise size preflop and heads-up, call mixed; small chance to 3-bet
                    if bet_fraction_of_pot <= 0.5:
                        if self.rng.random() < 0.55:
                            # Call
                            return PokerAction.CALL, 0
                        # 3-bet bluff occasionally
                        if min_raise > 0 and max_raise >= min_raise and self.rng.random() < 0.15:
                            # 3-bet: aim for 3x the amount_to_call as raise increment if possible
                            desired = max(min_raise, int(2.0 * amount_to_call))
                            desired = min(desired, max_raise)
                            if desired >= min_raise:
                                self.was_raiser_preflop = True
                                return PokerAction.RAISE, int(desired)
                        # Otherwise fold
                        return PokerAction.FOLD, 0
                    else:
                        # Big preflop bet faced: mostly fold; rare all-in with tiny prob if short
                        if remaining_chips <= max(self.blind_amount * 10, 20) and self.rng.random() < 0.05:
                            return PokerAction.ALL_IN, 0
                        return PokerAction.FOLD, 0
                else:
                    # Post-flop defense
                    # Call if small bet and pot odds reasonable
                    if bet_fraction_of_pot <= call_small_bet_thresh:
                        # Mix of calls and small raises as bluffs
                        roll = self.rng.random()
                        if roll < 0.70:
                            return PokerAction.CALL, 0
                        elif roll < 0.80 and min_raise > 0 and max_raise >= min_raise:
                            # Small bluff-raise with low frequency
                            desired = max(min_raise, int(0.5 * max(1, pot)))
                            desired = min(desired, max_raise)
                            if desired >= min_raise:
                                return PokerAction.RAISE, int(desired)
                        else:
                            return PokerAction.CALL, 0
                    else:
                        # For medium to large bets, compare pot odds threshold
                        # Without hole cards, be conservative: fold more to big bets; occasionally call
                        threshold = 0.28 if is_flop else (0.22 if is_turn else 0.18)
                        if call_pot_odds <= threshold and self.rng.random() < 0.40:
                            return PokerAction.CALL, 0
                        # Rare hero-call on river if bet is tiny relative to pot
                        if is_river and bet_fraction_of_pot <= 0.15 and self.rng.random() < 0.35:
                            return PokerAction.CALL, 0
                        # Rare all-in bluff if very short and multiway collapsed
                        if remaining_chips <= max(self.blind_amount * 8, 16) and self.rng.random() < 0.03:
                            return PokerAction.ALL_IN, 0
                        return PokerAction.FOLD, 0

        except Exception:
            # Safe fallback to avoid invalid actions
            try:
                # Attempt to check if possible, else fold
                my_id_str = str(self.id)
                me_bet = int(round_state.player_bets.get(my_id_str, 0)) if round_state.player_bets else 0
                current_bet = int(round_state.current_bet or 0)
                amount_to_call = max(0, current_bet - me_bet)
                if amount_to_call == 0:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0
            except Exception:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update session stats if possible
        try:
            if self.starting_chips:
                # This relies on per-round deltas being available as remaining_chips drift
                pass
            self.hands_played += 1
        except Exception:
            pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        try:
            # player_score is delta money across the game
            self.total_profit += int(player_score or 0)
        except Exception:
            pass

    # ---------------- Helper methods ----------------

    def _estimate_active_players(self, round_state: RoundStateClient) -> int:
        # Try to estimate number of active players (not folded)
        try:
            # If player_actions exist, count those not folded
            if round_state.player_actions:
                not_folded = 0
                for k, v in round_state.player_actions.items():
                    if str(v).lower() != 'fold':
                        not_folded += 1
                # If zero (no actions yet), fallback
                if not_folded > 0:
                    return not_folded
            # Fallback to number of betting entries or current players list length
            if round_state.current_player:
                return max(2, len(round_state.current_player))
            if round_state.player_bets:
                return max(2, len(round_state.player_bets))
        except Exception:
            pass
        return 2