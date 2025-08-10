from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 0
        self.hand = []
        self.position = 0
        self.num_players = 0
        self.player_id = None
        self.is_big_blind = False
        self.is_small_blind = False

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.player_id = str(self.id)
        self.is_big_blind = (big_blind_player_id == self.id)
        self.is_small_blind = (small_blind_player_id == self.id)
        self.num_players = len(all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.hand = player_hands.get(self.player_id, [])

    def evaluate_hand_strength(self, hand: List[str], community_cards: List[str]) -> float:
        """Evaluates the strength of a hand (0 to 1)"""
        # Simplified hand evaluation based on card ranks and potential for improvement
        if not hand:
            return 0.0

        ranks = '23456789TJQKA'
        rank_values = {r: i for i, r in enumerate(ranks)}
        
        # Convert hand and community cards to tuples of (rank, suit)
        all_cards = hand + community_cards
        card_ranks = [card[0] for card in all_cards]
        card_suits = [card[1] for card in all_cards]
        
        # Count occurrences of each rank and suit
        rank_counts = {}
        suit_counts = {}
        for r in card_ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        for s in card_suits:
            suit_counts[s] = suit_counts.get(s, 0) + 1
            
        # Calculate base strength
        max_rank_value = max([rank_values[r] for r in card_ranks])
        base_strength = max_rank_value / 12.0  # Normalize between 0 and 1 based on highest rank value
        
        # Check for pairs, trips, etc.
        pair_bonus = 0
        three_of_kind_bonus = 0
        four_of_kind_bonus = 0
        flush_potential_bonus = 0
        
        for count in rank_counts.values():
            if count == 2:
                pair_bonus += 0.1
            elif count == 3:
                three_of_kind_bonus += 0.2
            elif count == 4:
                four_of_kind_bonus += 0.4
                
        # Check for flush potential
        for count in suit_counts.values():
            if count >= 4:
                flush_potential_bonus += 0.15
            elif count == 5:
                flush_potential_bonus += 0.3
                
        # Add bonuses
        total_strength = base_strength + pair_bonus + three_of_kind_bonus + four_of_kind_bonus + flush_potential_bonus
        
        # Cap at 1.0
        return min(total_strength, 1.0)

    def should_fold(self, round_state: RoundStateClient, remaining_chips: int) -> bool:
        # Fold if hand is weak and there's any bet to call
        if round_state.current_bet > 0:
            strength = self.evaluate_hand_strength(self.hand, round_state.community_cards)
            
            # Preflop specific logic
            if round_state.round == 'Preflop':
                # Fold very weak hands pre-flop unless it's a small bet
                if strength < 0.3:
                    bet_ratio = round_state.current_bet / max(remaining_chips, 1)
                    if bet_ratio > 0.1:
                        return True
                        
            # Post-flop logic
            else:
                # Fold on weak hands when facing bets
                pot_odds = round_state.current_bet / max(round_state.pot, 1)
                if strength < pot_odds:
                    return True
                    
        return False

    def should_raise(self, round_state: RoundStateClient, remaining_chips: int) -> bool:
        # Aggressive raising with strong hands or in late position
        strength = self.evaluate_hand_strength(self.hand, round_state.community_cards)
        
        # Pre-flop: Raise with premium hands
        if round_state.round == 'Preflop':
            if strength > 0.7:
                return True
        # Post-flop: Raise with strong hands
        else:
            if strength > 0.6:
                return True
        
        return False

    def calculate_raise_amount(self, round_state: RoundStateClient, remaining_chips: int, aggression_factor: float = 1.0) -> int:
        """Calculates an appropriate raise amount based on pot size and hand strength"""
        # Standard raise sizing: 2.5x to 4x current bet depending on hand strength and aggression
        base_raise = round_state.current_bet * 2.5
        max_raise = round_state.max_raise
        min_raise = round_state.min_raise
        
        # Cap at available chips
        if base_raise > remaining_chips:
            base_raise = remaining_chips
            
        # Ensure within valid range
        if base_raise < min_raise:
            base_raise = min_raise
        if base_raise > max_raise:
            base_raise = max_raise
            
        return int(base_raise)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # If we have no remaining chips, fold
        if remaining_chips <= 0:
            return (PokerAction.FOLD, 0)
            
        # Evaluate hand strength
        hand_strength = self.evaluate_hand_strength(self.hand, round_state.community_cards)
        
        # Handle case where we can't make any valid action
        if round_state.min_raise > round_state.max_raise:
            # Can't raise, so decide between fold, check/call
            if round_state.current_bet == 0:
                return (PokerAction.CHECK, 0)
            else:
                # Current bet exists, we can only call or fold
                call_amount = round_state.current_bet - round_state.player_bets.get(self.player_id, 0)
                if call_amount > remaining_chips:
                    # Cannot afford to call, must fold or go all-in
                    return (PokerAction.FOLD, 0)
                elif call_amount == remaining_chips:
                    return (PokerAction.ALL_IN, 0)
                else:
                    if self.should_fold(round_state, remaining_chips):
                        return (PokerAction.FOLD, 0)
                    else:
                        return (PokerAction.CALL, 0)
        
        # Decision tree based on game state
        # No bet yet - can check or raise
        if round_state.current_bet == 0:
            if self.should_raise(round_state, remaining_chips):
                raise_amount = self.calculate_raise_amount(round_state, remaining_chips)
                return (PokerAction.RAISE, raise_amount)
            else:
                return (PokerAction.CHECK, 0)
                
        # There's a bet - need to call, raise, fold or go all-in
        else:
            call_amount = round_state.current_bet - round_state.player_bets.get(self.player_id, 0)
            
            # If we don't have enough to call, we can only fold or go all-in
            if call_amount > remaining_chips:
                if self.should_fold(round_state, remaining_chips):
                    return (PokerAction.FOLD, 0)
                else:
                    return (PokerAction.ALL_IN, 0)
                    
            # If call amount equals remaining chips, go all-in
            elif call_amount == remaining_chips:
                if self.should_fold(round_state, remaining_chips):
                    return (PokerAction.FOLD, 0)
                else:
                    return (PokerAction.ALL_IN, 0)
                    
            # Otherwise we can make normal decisions
            else:
                # Fold if hand is too weak
                if self.should_fold(round_state, remaining_chips):
                    return (PokerAction.FOLD, 0)
                    
                # Check if we want to raise
                elif self.should_raise(round_state, remaining_chips):
                    raise_amount = self.calculate_raise_amount(round_state, remaining_chips)
                    return (PokerAction.RAISE, raise_amount)
                    
                # Otherwise just call
                else:
                    return (PokerAction.CALL, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Nothing to do here for now
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Nothing to do here for now
        pass