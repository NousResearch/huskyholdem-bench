from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import itertools
import collections

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 0
        self.my_hand = []
        self.blind_amount = 0
        self.big_blind_player_id = 0
        self.small_blind_player_id = 0
        self.all_players = []
        self.player_id = None
        self.remaining_chips = 0
        self.round_num = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.my_hand = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.remaining_chips = remaining_chips
        self.round_num = round_state.round_num

    def evaluate_hand_strength(self, hand: List[str], community_cards: List[str]) -> float:
        """Evaluate hand strength from 0 to 1"""
        all_cards = hand + community_cards
        
        if len(all_cards) < 5:
            return self._preflop_strength(hand)
        
        # For full evaluation, we'll use a simplified approach
        # In real implementation, you'd want proper hand ranking
        return self._simple_hand_eval(hand, community_cards)
    
    def _preflop_strength(self, hand: List[str]) -> float:
        """Evaluate preflop hand strength"""
        ranks = [card[0] for card in hand]
        suits = [card[1] for card in hand]
        
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        rank1, rank2 = ranks
        value1, value2 = rank_values[rank1], rank_values[rank2]
        
        # Pocket pairs
        if rank1 == rank2:
            if value1 >= 10:  # High pocket pairs
                return 0.8
            elif value1 >= 7:  # Medium pocket pairs
                return 0.6
            else:  # Small pocket pairs
                return 0.4
        
        # High cards
        high_card_value = max(value1, value2)
        suited = suits[0] == suits[1]
        
        if high_card_value >= 12:  # At least one high card (Q, K, A)
            if abs(value1 - value2) <= 4 and suited:  # Connected suited
                return 0.7
            elif suited or abs(value1 - value2) <= 4:  # Suited or connected
                return 0.6
            else:
                return 0.5
        elif high_card_value >= 10:  # At least one decent card (T, J)
            if suited:
                return 0.5
            else:
                return 0.4
        else:  # Low cards
            if suited and abs(value1 - value2) <= 2:  # Small suited connectors
                return 0.4
            else:
                return 0.2
    
    def _simple_hand_eval(self, hand: List[str], community_cards: List[str]) -> float:
        """Simple hand evaluation"""
        # This is a simplified version - in reality you'd want full poker hand evaluation
        all_cards = hand + community_cards
        ranks = [card[0] for card in all_cards]
        suits = [card[1] for card in all_cards]
        
        rank_counts = collections.Counter(ranks)
        suit_counts = collections.Counter(suits)
        
        # Count pairs, trips, etc.
        pairs = sum(1 for count in rank_counts.values() if count == 2)
        trips = sum(1 for count in rank_counts.values() if count == 3)
        quads = sum(1 for count in rank_counts.values() if count == 4)
        
        # Flush potential
        flush_potential = max(suit_counts.values())
        
        # Straight potential (simplified)
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        unique_ranks = sorted(set(rank_values[r] for r in ranks))
        
        # Check for straight potential
        straight_potential = 0
        if len(unique_ranks) >= 4:
            for i in range(len(unique_ranks) - 3):
                if unique_ranks[i+3] - unique_ranks[i] <= 4:
                    straight_potential = 1
                    break
        
        # Basic hand strength calculation
        strength = 0.1  # Default
        
        if quads:
            strength = 0.95
        elif trips and pairs:
            strength = 0.9
        elif trips:
            strength = 0.8
        elif pairs >= 2:
            strength = 0.7
        elif pairs:
            strength = 0.6
        elif flush_potential >= 4:
            strength = 0.65
        elif straight_potential:
            strength = 0.55
        elif max(rank_values[r] for r in ranks) >= 12:  # Has high card
            strength = 0.45
        elif flush_potential >= 3:
            strength = 0.4
        
        return min(strength, 0.95)  # Cap at 0.95

    def calculate_pot_odds(self, call_amount: int, pot_size: int) -> float:
        """Calculate pot odds"""
        if call_amount <= 0:
            return 1.0
        return pot_size / (pot_size + call_amount)

    def should_call_based_on_odds(self, hand_strength: float, pot_odds: float) -> bool:
        """Determine if we should call based on hand strength and pot odds"""
        return hand_strength >= pot_odds * 0.7  # Require some edge

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            # Get current bet information
            current_bet = round_state.current_bet
            my_current_bet = round_state.player_bets.get(str(self.id), 0)
            call_amount = current_bet - my_current_bet
            
            # Calculate pot odds
            pot_odds = self.calculate_pot_odds(call_amount, round_state.pot)
            
            # Evaluate hand strength
            hand_strength = self.evaluate_hand_strength(self.my_hand, round_state.community_cards)
            
            # Determine action based on round and hand strength
            if round_state.round == "Preflop":
                action = self._preflop_decision(hand_strength, call_amount, round_state)
            else:
                action = self._postflop_decision(hand_strength, call_amount, round_state, pot_odds)
            
            # Handle betting amounts
            if action[0] == PokerAction.RAISE:
                raise_amount = action[1]
                # Ensure raise is within limits
                min_raise = round_state.min_raise
                max_raise = round_state.max_raise
                
                if raise_amount < min_raise:
                    raise_amount = min_raise
                if raise_amount > max_raise:
                    raise_amount = max_raise
                    
                return (PokerAction.RAISE, raise_amount)
            else:
                return action
                
        except Exception as e:
            # Fallback to safe play
            return (PokerAction.FOLD, 0)

    def _preflop_decision(self, hand_strength: float, call_amount: int, round_state: RoundStateClient) -> Tuple[PokerAction, int]:
        """Make preflop decision"""
        # Position awareness - are we in early, middle, or late position?
        # For simplification, we'll assume we're always in a standard position
        
        # If we can check, do so with weak hands
        if call_amount == 0:
            if hand_strength >= 0.4:  # Playable hand
                return (PokerAction.RAISE, min(20, round_state.max_raise))  # Small raise
            else:
                return (PokerAction.CHECK, 0)
        
        # We need to call or fold
        if hand_strength >= 0.6:  # Decent hand
            if call_amount <= 20:  # Reasonable call
                return (PokerAction.CALL, 0)
            elif hand_strength >= 0.8 and call_amount <= 50:  # Strong hand
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        elif hand_strength >= 0.4 and call_amount <= 10:  # Marginal hand but cheap to call
            return (PokerAction.CALL, 0)
        else:
            return (PokerAction.FOLD, 0)

    def _postflop_decision(self, hand_strength: float, call_amount: int, round_state: RoundStateClient, pot_odds: float) -> Tuple[PokerAction, int]:
        """Make postflop decision"""
        # If we can check, consider doing so
        if call_amount == 0:
            if hand_strength >= 0.7:  # Strong hand
                return (PokerAction.RAISE, min(30, round_state.max_raise))  # Value bet
            elif hand_strength >= 0.5:  # Decent hand
                return (PokerAction.CHECK, 0)
            else:
                return (PokerAction.CHECK, 0)  # Always check with weak hands
        
        # Need to call or fold
        if hand_strength >= 0.8:  # Strong hand
            if call_amount <= 30 or self.should_call_based_on_odds(hand_strength, pot_odds):
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        elif hand_strength >= 0.6:  # Medium hand
            if call_amount <= 15 and self.should_call_based_on_odds(hand_strength, pot_odds):
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        elif hand_strength >= 0.4 and call_amount <= 5 and self.should_call_based_on_odds(hand_strength, pot_odds):  # Cheap call with drawing hand
            return (PokerAction.CALL, 0)
        else:
            return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the end of the round."""
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """Called at the end of the game."""
        pass