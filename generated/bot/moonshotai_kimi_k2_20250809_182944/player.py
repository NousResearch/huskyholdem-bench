from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 10000
        self.blind_amount = 0
        self.hand_strength_cache = {}
        self.player_stats = {}
        self.position = None
        self.stack_size = 10000
        self.current_hand = []
        self.community_cards = []
        self.bet_history = {'PreFlop': [], 'Flop': [], 'Turn': [], 'River': []}
        self.aggression_factor = 0
        self.tightness_factor = 0
        self.table_image = 'tight'
        self.pot_odds = 0
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.all_players = all_players
        self.position = 'late' if len(all_players) <= 3 else 'middle'
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.stack_size = remaining_chips
        self.bet_history['PreFlop'] = []
        self.bet_history['Flop'] = []
        self.bet_history['Turn'] = []
        self.bet_history['River'] = []
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        if round_state.current_bet > self.stack_size:
            return PokerAction.FOLD, 0
            
        # Calculate hand strength
        hand_strength = self.evaluate_hand_strength(round_state.community_cards)
        pot_odds = self.calculate_pot_odds(round_state)
        
        # Position-based strategy
        is_late_position = self.is_late_position(round_state)
        aggression_multiplier = 1.2 if is_late_position else 0.8
        
        # Determine action based on hand strength and situation
        if hand_strength > 0.9 and round_state.round == 'Preflop':
            return PokerAction.RAISE, min(round_state.current_bet * 3, self.stack_size)
        elif hand_strength > 0.8 and round_state.round in ['Flop', 'Turn']:
            if round_state.current_bet == 0:
                return PokerAction.RAISE, min(round_state.pot * 0.75, self.stack_size)
            elif pot_odds > 0.3:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        elif hand_strength > 0.6:
            if round_state.current_bet == 0 and is_late_position:
                return PokerAction.RAISE, min(round_state.pot * 0.5, self.stack_size)
            elif pot_odds > 0.25:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        else:
            if round_state.current_bet == 0:
                return PokerAction.CHECK, 0
            elif pot_odds > 0.4:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
                
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        self.stack_size = remaining_chips
        
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        self.adjust_strategy_based_on_results(all_scores, active_players_hands)
        
    def evaluate_hand_strength(self, community_cards: List[str]) -> float:
        """Evaluate hand strength based on hole cards and potential"""
        if not self.hand_strength_cache:
            return 0.5
            
        score = 0.0
        if len(community_cards) >= 3:
            # Basic evaluation - pairs, suited connectors, etc.
            ranks = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
            
            hole_ranks = []
            hole_suits = []
            # This is simplified - would need actual hole cards
            score = random.random() * 0.7 + 0.3
            
        return score
        
    def calculate_pot_odds(self, round_state: RoundStateClient) -> float:
        if round_state.current_bet == 0:
            return 0.0
            
        amount_to_call = round_state.current_bet
        potential_gain = round_state.pot
        pot_odds = amount_to_call / (potential_gain + amount_to_call)
        return pot_odds
        
    def is_late_position(self, round_state: RoundStateClient) -> bool:
        return len(self.all_players) <= 3
        
    def adjust_strategy_based_on_results(self, all_scores: dict, active_players_hands: dict):
        # Update table image and adjust strategy based on performance
        pass