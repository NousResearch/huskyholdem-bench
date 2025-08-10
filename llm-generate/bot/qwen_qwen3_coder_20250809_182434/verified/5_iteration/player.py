from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 10000
        self.hand = []
        self.blind_amount = 0
        self.big_blind_player_id = 0
        self.small_blind_player_id = 0
        self.all_players = []
        self.remaining_chips = 0
        self.round_state = None

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.round_state = round_state
        self.remaining_chips = remaining_chips
        # Fix error: player_hands is not available in this context
        # Hand assignment should happen in on_start or get_action based on context
        pass

    def evaluate_hand_strength(self, hand: List[str], community_cards: List[str]) -> float:
        """Simple hand strength evaluation"""
        # This is a very basic heuristic
        # In a real implementation, you would use a proper hand evaluator
        # For now, we'll use a simplified approach
        
        # High card values
        card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        # Check for pairs, suited cards, etc.
        hand_ranks = [card[0] for card in hand]
        hand_suits = [card[1] for card in hand]
        
        # Basic strength calculation
        strength = 0
        
        # Pair bonus
        if hand_ranks[0] == hand_ranks[1]:
            strength += 0.3
            
        # High cards
        high_card_value = max(card_values[hand_ranks[0]], card_values[hand_ranks[1]])
        strength += high_card_value / 14 * 0.4
        
        # Suited bonus
        if hand_suits[0] == hand_suits[1]:
            strength += 0.2
            
        # Connected cards bonus
        diff = abs(card_values[hand_ranks[0]] - card_values[hand_ranks[1]])
        if diff == 1:  # Connected
            strength += 0.1
        elif diff == 2:  # One gap
            strength += 0.05
            
        return min(strength, 1.0)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Preflop strategy
        if round_state.round == "Preflop":
            # Evaluate hand strength
            hand_strength = self.evaluate_hand_strength(self.hand, [])
            
            # Positional awareness
            is_big_blind = self.id == self.big_blind_player_id
            is_small_blind = self.id == self.small_blind_player_id
            
            # Required to call
            required_to_call = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
            
            # Aggressive preflop with strong hands
            if hand_strength > 0.7:
                if required_to_call == 0:
                    # We can raise
                    raise_amount = min(round_state.max_raise, max(round_state.min_raise, round_state.current_bet * 2))
                    return (PokerAction.RAISE, raise_amount)
                elif required_to_call <= remaining_chips * 0.1:
                    # Reasonable call
                    return (PokerAction.CALL, 0)
                else:
                    # Too expensive, fold
                    return (PokerAction.FOLD, 0)
            elif hand_strength > 0.4:
                # Medium strength hands
                if required_to_call == 0:
                    # We can check or make a small raise
                    if is_big_blind:
                        return (PokerAction.CHECK, 0)
                    else:
                        raise_amount = min(round_state.max_raise, round_state.min_raise)
                        return (PokerAction.RAISE, raise_amount)
                elif required_to_call <= remaining_chips * 0.05:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                # Weak hands
                if required_to_call == 0:
                    # We can check
                    return (PokerAction.CHECK, 0)
                elif is_small_blind and required_to_call <= self.blind_amount:
                    # Defend small blind with weak hands sometimes
                    if random.random() < 0.3:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                else:
                    return (PokerAction.FOLD, 0)
        
        # Postflop strategy
        else:
            # Simplified postflop play
            required_to_call = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
            
            # Always allow checking when no bet is required
            if required_to_call == 0:
                # Let's sometimes bet for value/protection
                if random.random() < 0.4:  # 40% of the time bet
                    bet_size = min(round_state.max_raise, max(round_state.min_raise, int(round_state.pot * 0.5)))
                    return (PokerAction.RAISE, bet_size)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                # There's a bet to call
                pot_odds = required_to_call / (round_state.pot + required_to_call) if (round_state.pot + required_to_call) > 0 else 0
                
                # Call if pot odds are reasonable (simplified)
                if pot_odds < 0.3 or required_to_call < remaining_chips * 0.1:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        
        # Default fallback
        return (PokerAction.CHECK, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update our chip count
        self.remaining_chips = remaining_chips

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Game ended, could log results or adjust strategy
        pass