from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from enum import Enum

class PokerRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.player_id = None

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.hole_cards = player_hands
        # We assume player_id is set by set_id method of the Bot superclass

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.hole_cards = round_state.player_hands[str(self.id)] if str(self.id) in round_state.player_hands else []

    def _get_card_value(self, card: str) -> int:
        """Returns the numerical value of a card (2-14, 14 for Ace)."""
        rank = card[0]
        if rank == 'T':
            return 10
        elif rank == 'J':
            return 11
        elif rank == 'Q':
            return 12
        elif rank == 'K':
            return 13
        elif rank == 'A':
            return 14
        else:
            return int(rank)

    def _get_suit(self, card: str) -> str:
        """Returns the suit of a card."""
        return card[1]

    def _is_pair(self, hand: List[str]) -> bool:
        """Checks if the hand contains a pair."""
        if len(hand) != 2:
            return False
        return self._get_card_value(hand[0]) == self._get_card_value(hand[1])

    def _is_suited(self, hand: List[str]) -> bool:
        """Checks if the hand is suited."""
        if len(hand) != 2:
            return False
        return self._get_suit(hand[0]) == self._get_suit(hand[1])

    def _is_connector(self, hand: List[str]) -> bool:
        """Checks if the hand is a connector (sequential ranks)."""
        if len(hand) != 2:
            return False
        val1 = self._get_card_value(hand[0])
        val2 = self._get_card_value(hand[1])
        return abs(val1 - val2) == 1

    def _calculate_preflop_strength(self) -> float:
        """Calculates a simplified pre-flop hand strength."""
        if not self.hole_cards or len(self.hole_cards) != 2:
            return 0.0

        val1 = self._get_card_value(self.hole_cards[0])
        val2 = self._get_card_value(self.hole_cards[1])

        # Always ensure val1 is the higher card for consistency
        if val1 < val2:
            val1, val2 = val2, val1

        strength = 0.0

        # Pairs
        if val1 == val2:
            if val1 >= 10:  # TT+
                strength = 0.9
            elif val1 >= 7: # 77-99
                strength = 0.7
            else:           # 22-66
                strength = 0.5
        # Suited connectors
        elif self._is_suited(self.hole_cards) and self._is_connector(self.hole_cards):
            if val1 >= 10: # TJss+
                strength = 0.75
            elif val1 >= 7: # 78ss-9Tss
                strength = 0.6
            else:           # lower suited connectors
                strength = 0.4
        # Suited aces
        elif self._is_suited(self.hole_cards) and val1 == 14: # Axs
            strength = 0.65
        # Broadways (AK, AQ, AJ, AT, KQ, KJ, KT, QJ, QT, JT)
        elif val1 >= 10 and val2 >= 10:
            if self._is_suited(self.hole_cards):
                strength = 0.8
            else:
                strength = 0.7
        # Other high cards
        elif val1 >= 12: # Qx+, Kx+
            if self._is_suited(self.hole_cards):
                strength = 0.55
            else:
                strength = 0.45
        else: # Any other hand
            strength = 0.1 # Default weak hand

        # Add a small randomness to avoid perfectly predictable behavior
        # strength += (random.random() - 0.5) * 0.05
        # strength = max(0.0, min(1.0, strength)) # Keep between 0 and 1
        return strength

    def _get_current_bet_to_call(self, round_state: RoundStateClient) -> int:
        """Calculates the amount needed to call."""
        player_id_str = str(self.id)
        player_current_bet = round_state.player_bets.get(player_id_str, 0)
        return max(0, round_state.current_bet - player_current_bet)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        current_bet_to_call = self._get_current_bet_to_call(round_state)
        min_raise = round_state.min_raise
        max_raise = round_state.max_raise
        # Ensure min_raise is never less than current_bet_to_call + big blind for realism in later streets
        # This will be handled by the game server if min_raise is too low, but for our bot's logic:
        # min_raise = max(min_raise, round_state.current_bet * 2 - round_state.player_bets.get(str(self.id), 0))
        # No, a raise must be at least the previous raise amount. The current_bet IS the last action amount.
        # A raise must be at least current_bet + min_raise_increment.
        # Let's consider `min_raise` from round_state as the minimum amount to raise *above* the current bet.
        # So, total amount to bet for a min raise is current_bet + min_raise.
        # But `min_raise` in `RoundStateClient` means the total amount a raise needs to be to be valid.
        # This is `current_bet + (last_raise_amount or big_blind)`.
        # So, the actual amount to *add* to current_bet is `min_raise - current_bet`.
        
        # Correct interpretation: min_raise is the minimum total bet that constitutes a raise.
        # So, if current_bet is 10 and min_raise is 20, you need to bet 20 total.
        # The amount to add on top of what you've already bet is `min_raise - player_current_bet`.
        
        player_current_bet_this_round = round_state.player_bets.get(str(self.id), 0)
        
        # Calculate amount to raise by
        # If current_bet is 0 (first to act or everyone checked), min_raise is usually big blind.
        # If current_bet is > 0, min_raise is (current_bet + last_bet_amount_added_to_pot_by_raiser)
        # So if current_bet is 100, and previous player *raised* from 50 to 100 (added 50),
        # min_raise should be 100 + 50 = 150.
        # The `min_raise` provided by `RoundStateClient` already adjusts for this, it's the target total bet for a min raise.
        
        amount_needed_for_min_raise = min_raise - player_current_bet_this_round

        # Heuristic actions
        preflop_strength = self._calculate_preflop_strength()

        # Handle different betting rounds
        if round_state.round == 'PREFLOP':
            # Aggressive play with strong hands, cautious with weak hands
            if preflop_strength >= 0.7:  # Premium hands (AA, KK, AKs, etc.)
                if remaining_chips >= max_raise: # Can all-in
                    return PokerAction.ALL_IN, 0
                elif current_bet_to_call > 0 and remaining_chips >= amount_needed_for_min_raise:
                    # If there's a bet, raise
                    return PokerAction.RAISE, amount_needed_for_min_raise
                elif remaining_chips >= self.blind_amount * 3: # If no bet, make aggressive opening raise
                    return PokerAction.RAISE, self.blind_amount * 3
                else: # Fallback to call or all-in if cannot raise full amount
                    if current_bet_to_call > 0:
                        if remaining_chips >= current_bet_to_call:
                            return PokerAction.CALL, 0
                        else:
                            return PokerAction.ALL_IN, 0 # Cannot call, all-in what's left
                    else:
                        return PokerAction.CHECK, 0 # No bet, check if possible
            elif preflop_strength >= 0.5:  # Medium hands (suited connectors, smaller pairs, Axs)
                if current_bet_to_call == 0:  # No raise yet, open with a small raise or check
                    if remaining_chips >= self.blind_amount * 2:
                        return PokerAction.RAISE, self.blind_amount * 2
                    else:
                        return PokerAction.CHECK, 0
                elif current_bet_to_call <= self.blind_amount * 2: # Small bet, call
                    if remaining_chips >= current_bet_to_call:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.ALL_IN, 0 # Cannot call, all-in
                else:  # Too expensive to call, or cannot afford min raise
                    if remaining_chips > 0 and current_bet_to_call < remaining_chips: # Only fold if we can't afford to call
                        return PokerAction.FOLD, 0
                    elif remaining_chips <= current_bet_to_call: # Cannot call fully, all-in
                        return PokerAction.ALL_IN, 0
            else:  # Weak hands
                if current_bet_to_call == 0:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0
        
        # Post-flop strategy (simplified)
        # This bot doesn't evaluate community cards, it plays based on a static approach
        # This will need improvement in future iterations.
        
        # General post-flop strategy:
        # If there's no bet, check.
        # If there's a bet, call if it's small relative to stack, otherwise fold unless holding strong preflop hand.
        # Aggressively bet/raise with very strong preflop hands.
        
        if current_bet_to_call == 0:
            return PokerAction.CHECK, 0
        else:
            # If current bet is less than 10% of remaining chips, consider calling
            if current_bet_to_call <= remaining_chips * 0.1:
                if remaining_chips >= current_bet_to_call:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.ALL_IN, 0 # All-in if can't call full amount
            # If current bet is higher, only call or raise with premium hands
            elif preflop_strength >= 0.6: # Continue with strong hands
                if remaining_chips >= amount_needed_for_min_raise:
                    return PokerAction.RAISE, amount_needed_for_min_raise
                elif remaining_chips >= current_bet_to_call:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.ALL_IN, 0
            else: # Fold weak/medium hands to significant bets
                return PokerAction.FOLD, 0
        
        # Fallback to fold if no other action is determined (should not happen with comprehensive logic)
        return PokerAction.FOLD, 0


    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Reset hole cards for the next round
        self.hole_cards = []

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass # No specific action needed at the end of the entire game