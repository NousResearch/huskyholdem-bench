from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.player_id = None
        self.hole_cards = []
        self.starting_chips = 10000
        self.my_current_bet = 0
        self.hand_strength = 0.0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.player_id = self.id
        self.starting_chips = starting_chips
        self.hole_cards = player_hands

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.my_current_bet = round_state.player_bets.get(str(self.player_id), 0)

    def evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        """Basic hand evaluation based on hole cards and community cards"""
        # Very basic evaluation - in reality, this should be much more sophisticated
        # This is just a placeholder for now
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        if not self.hole_cards or len(self.hole_cards) < 2:
            return 0.0
            
        card1 = self.hole_cards[0]
        card2 = self.hole_cards[1]
        
        # Extract ranks and suits
        rank1 = card1[:-1] if card1 else '2'
        suit1 = card1[-1] if card1 else 'h'
        rank2 = card2[:-1] if card2 else '2'
        suit2 = card2[-1] if card2 else 'h'
        
        # Basic hand strength
        rank_val1 = rank_values.get(rank1, 2)
        rank_val2 = rank_values.get(rank2, 2)
        
        # Pair bonus
        pair_bonus = 0.2 if rank1 == rank2 else 0
        
        # High card bonus
        high_card_bonus = (max(rank_val1, rank_val2) - 10) * 0.05 if max(rank_val1, rank_val2) > 10 else 0
        
        # Suited bonus
        suited_bonus = 0.1 if suit1 == suit2 else 0
        
        # Base strength
        base_strength = (rank_val1 + rank_val2) / 28.0  # Normalize by max possible sum
        
        return base_strength + pair_bonus + high_card_bonus + suited_bonus

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Update current bet
        self.my_current_bet = round_state.player_bets.get(str(self.player_id), 0)
        
        # Calculate hand strength
        self.hand_strength = self.evaluate_hand_strength(round_state)
        
        # Calculate how much more we need to call
        amount_to_call = round_state.current_bet - self.my_current_bet
        
        # Calculate pot odds
        pot_odds = amount_to_call / (round_state.pot + amount_to_call) if (round_state.pot + amount_to_call) > 0 else 0
        
        # Pre-flop strategy
        if round_state.round == 'Preflop':
            return self._preflop_strategy(round_state, remaining_chips, amount_to_call)
        else:
            # Post-flop strategy
            return self._postflop_strategy(round_state, remaining_chips, amount_to_call, pot_odds)

    def _preflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, amount_to_call: int) -> Tuple[PokerAction, int]:
        # Very basic preflop strategy based on hand strength
        if self.hand_strength > 0.7:  # Premium hands
            if amount_to_call == 0:
                # We can check, so raise for value
                raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.03)), remaining_chips)
                if raise_amount > 0 and raise_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.CALL, 0)  # fallback
            else:
                # There's a bet, we have a strong hand
                if amount_to_call <= remaining_chips * 0.1:  # Reasonable bet
                    return (PokerAction.CALL, 0)
                else:
                    # Large bet but strong hand
                    if self.hand_strength > 0.85 or random.random() < 0.3:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
        elif self.hand_strength > 0.4:  # Decent hands
            if amount_to_call == 0:
                # We can check
                return (PokerAction.CHECK, 0)
            elif amount_to_call <= remaining_chips * 0.05:  # Small bet
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        else:  # Weak hands
            if amount_to_call == 0:
                # We can check
                return (PokerAction.CHECK, 0)
            elif amount_to_call <= remaining_chips * 0.02:  # Tiny bet
                if random.random() < 0.2:  # Occasionally call
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                return (PokerAction.FOLD, 0)

    def _postflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, amount_to_call: int, pot_odds: float) -> Tuple[PokerAction, int]:
        # Simple post-flop strategy
        if self.hand_strength > 0.6:  # Strong post-flop
            if amount_to_call == 0:
                # Value bet
                raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.05)), remaining_chips)
                if raise_amount > 0 and raise_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                # Call or raise for value
                if self.hand_strength > 0.7 or amount_to_call <= remaining_chips * 0.15:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        elif self.hand_strength > 0.3:  # Medium strength
            if amount_to_call == 0:
                if random.random() < 0.5:
                    # Try a probe bet
                    raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.02)), remaining_chips)
                    if raise_amount > 0 and raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, raise_amount)
                    else:
                        return (PokerAction.CHECK, 0)
                else:
                    return (PokerAction.CHECK, 0)
            elif pot_odds < 0.3 and amount_to_call <= remaining_chips * 0.08:  # Getting good odds
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        else:  # Weak
            if amount_to_call == 0:
                # Check and potentially bluff later
                if round_state.round == 'River' and random.random() < 0.3:
                    # Bluff on river sometimes
                    raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.05)), remaining_chips)
                    if raise_amount > 0 and raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, raise_amount)
                    else:
                        return (PokerAction.CHECK, 0)
                else:
                    return (PokerAction.CHECK, 0)
            elif amount_to_call <= remaining_chips * 0.03:  # Very small bet
                if random.random() < 0.1:  # Call occasionally with weak hand
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Reset for next round
        self.my_current_bet = 0

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Game ended, cleanup if needed
        pass