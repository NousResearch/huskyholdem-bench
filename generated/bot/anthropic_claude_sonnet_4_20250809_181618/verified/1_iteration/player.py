from typing import List, Tuple, Dict
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.all_players = []
        self.player_stats = {}  # Track opponent behavior
        self.hand_history = []
        self.position_factor = 1.0
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.hole_cards = player_hands
        self.blind_amount = blind_amount
        self.all_players = all_players
        
        # Initialize player stats tracking
        for player_id in all_players:
            if player_id != self.id:
                self.player_stats[player_id] = {
                    'hands_played': 0,
                    'aggressive_actions': 0,
                    'total_actions': 0,
                    'fold_to_raise': 0,
                    'raises_faced': 0
                }
    
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Update position factor based on number of players and our position
        num_players = len(round_state.current_player)
        if num_players > 1:
            our_position = round_state.current_player.index(self.id) if self.id in round_state.current_player else 0
            self.position_factor = 1.0 + (our_position / max(1, num_players - 1)) * 0.3
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Update opponent stats
        self._update_opponent_stats(round_state)
        
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength(round_state)
        
        # Calculate pot odds and betting dynamics
        pot_odds = self._calculate_pot_odds(round_state, remaining_chips)
        
        # Get aggression factor based on opponents
        aggression_factor = self._calculate_aggression_factor(round_state)
        
        # Calculate effective hand strength with position and dynamics
        effective_strength = hand_strength * self.position_factor * aggression_factor
        
        # Get call amount
        my_current_bet = round_state.player_bets.get(str(self.id), 0)
        call_amount = round_state.current_bet - my_current_bet
        
        # Stack management - be more conservative when short stacked
        stack_factor = remaining_chips / max(1, self.starting_chips)
        if stack_factor < 0.3:
            effective_strength *= 0.8  # More conservative when short
        elif stack_factor > 2.0:
            effective_strength *= 1.2  # More aggressive when deep
        
        # Decision making based on effective strength and pot odds
        if effective_strength < 0.15:
            return PokerAction.FOLD, 0
        
        elif effective_strength < 0.3:
            if call_amount == 0:
                return PokerAction.CHECK, 0
            elif pot_odds > 3.0 and call_amount < remaining_chips * 0.1:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        elif effective_strength < 0.5:
            if call_amount == 0:
                return PokerAction.CHECK, 0
            elif call_amount < remaining_chips * 0.15:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        elif effective_strength < 0.7:
            if call_amount == 0:
                # Sometimes bet for value/bluff
                if random.random() < 0.4:
                    bet_size = min(round_state.pot // 2, remaining_chips)
                    if bet_size >= round_state.min_raise:
                        return PokerAction.RAISE, bet_size
                return PokerAction.CHECK, 0
            elif call_amount < remaining_chips * 0.25:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        elif effective_strength < 0.85:
            if call_amount == 0:
                # Bet for value
                bet_size = min(round_state.pot * 2 // 3, remaining_chips)
                if bet_size >= round_state.min_raise:
                    return PokerAction.RAISE, bet_size
                return PokerAction.CHECK, 0
            elif call_amount < remaining_chips * 0.4:
                # Sometimes raise for value
                if random.random() < 0.6:
                    raise_size = min(call_amount + round_state.pot // 2, remaining_chips)
                    if raise_size >= round_state.min_raise and raise_size > call_amount:
                        return PokerAction.RAISE, raise_size
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        else:  # Very strong hand
            if call_amount == 0:
                bet_size = min(round_state.pot, remaining_chips)
                if bet_size >= round_state.min_raise:
                    return PokerAction.RAISE, bet_size
                return PokerAction.CHECK, 0
            elif call_amount < remaining_chips * 0.8:
                # Raise for value
                raise_size = min(call_amount + round_state.pot, remaining_chips)
                if raise_size >= round_state.min_raise and raise_size > call_amount:
                    return PokerAction.RAISE, raise_size
                return PokerAction.CALL, 0
            else:
                # Call even large bets with very strong hands
                return PokerAction.CALL, 0
    
    def _update_opponent_stats(self, round_state: RoundStateClient):
        for player_id_str, action in round_state.player_actions.items():
            player_id = int(player_id_str)
            if player_id != self.id and player_id in self.player_stats:
                self.player_stats[player_id]['total_actions'] += 1
                if action in ['Raise', 'All-in']:
                    self.player_stats[player_id]['aggressive_actions'] += 1
    
    def _calculate_aggression_factor(self, round_state: RoundStateClient):
        if not self.player_stats:
            return 1.0
        
        total_aggression = 0
        active_opponents = 0
        
        for player_id in round_state.current_player:
            if player_id != self.id and player_id in self.player_stats:
                stats = self.player_stats[player_id]
                if stats['total_actions'] > 0:
                    aggression_rate = stats['aggressive_actions'] / max(1, stats['total_actions'])
                    total_aggression += aggression_rate
                    active_opponents += 1
        
        if active_opponents == 0:
            return 1.0
        
        avg_aggression = total_aggression / active_opponents
        # Adjust our play based on opponent aggression
        return 1.0 - (avg_aggression * 0.3)  # Be more conservative vs aggressive opponents
    
    def _calculate_pot_odds(self, round_state: RoundStateClient, remaining_chips: int):
        my_current_bet = round_state.player_bets.get(str(self.id), 0)
        call_amount = round_state.current_bet - my_current_bet
        
        if call_amount <= 0:
            return float('inf')
        
        return round_state.pot / max(1, call_amount)
    
    def _evaluate_hand_strength(self, round_state: RoundStateClient):
        if not self.hole_cards:
            return 0.5
        
        # Pre-flop hand evaluation
        if round_state.round == 'Preflop':
            return self._evaluate_preflop_strength()
        
        # Post-flop evaluation
        all_cards = self.hole_cards + round_state.community_cards
        if len(all_cards) < 5:
            return self._evaluate_draw_strength(round_state)
        
        return self._evaluate_made_hand_strength(all_cards, round_state)
    
    def _evaluate_preflop_strength(self):
        if len(self.hole_cards) != 2:
            return 0.5
        
        card1, card2 = self.hole_cards
        rank1, suit1 = card1[0], card1[1]
        rank2, suit2 = card2[0], card2[1]
        
        # Convert face cards to numbers
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 7)
        val2 = rank_values.get(rank2, 7)
        
        is_pair = (rank1 == rank2)
        is_suited = (suit1 == suit2)
        high_card = max(val1, val2)
        low_card = min(val1, val2)
        
        # Base strength calculation
        if is_pair:
            if high_card >= 13:  # AA, KK
                return 0.95
            elif high_card >= 11:  # QQ, JJ
                return 0.85
            elif high_card >= 8:  # 88-TT
                return 0.7
            else:  # Small pairs
                return 0.6
        
        # Non-pair hands
        base_strength = (high_card + low_card) / 28.0
        
        # Suited bonus
        if is_suited:
            base_strength += 0.1
        
        # Connected bonus
        if abs(val1 - val2) == 1:
            base_strength += 0.05
        elif abs(val1 - val2) == 2:
            base_strength += 0.03
        
        # High card bonus
        if high_card == 14:  # Ace
            base_strength += 0.15
        elif high_card >= 12:  # King or Queen
            base_strength += 0.1
        
        return min(0.95, max(0.1, base_strength))
    
    def _evaluate_draw_strength(self, round_state: RoundStateClient):
        # Simple draw evaluation for flop/turn
        community = round_state.community_cards
        all_cards = self.hole_cards + community
        
        # Basic made hand strength
        base_strength = self._get_basic_hand_strength(all_cards)
        
        # Add draw potential
        if len(community) == 3:  # Flop
            draw_strength = self._evaluate_draws(all_cards)
            return min(0.9, base_strength + draw_strength * 0.3)
        elif len(community) == 4:  # Turn
            draw_strength = self._evaluate_draws(all_cards)
            return min(0.9, base_strength + draw_strength * 0.15)
        
        return base_strength
    
    def _evaluate_draws(self, cards):
        if len(cards) < 4:
            return 0
        
        suits = {}
        ranks = []
        
        for card in cards:
            rank, suit = card[0], card[1]
            suits[suit] = suits.get(suit, 0) + 1
            rank_val = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                       '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}.get(rank, 7)
            ranks.append(rank_val)
        
        draw_strength = 0
        
        # Flush draw
        for count in suits.values():
            if count == 4:
                draw_strength += 0.4  # Flush draw
        
        # Straight draw (simplified)
        ranks.sort()
        for i in range(len(ranks) - 3):
            consecutive = 1
            for j in range(i + 1, len(ranks)):
                if ranks[j] == ranks[j-1] + 1:
                    consecutive += 1
                elif ranks[j] != ranks[j-1]:
                    break
            if consecutive >= 3:
                draw_strength += 0.3  # Straight draw potential
                break
        
        return min(0.5, draw_strength)
    
    def _get_basic_hand_strength(self, cards):
        if len(cards) < 5:
            return 0.3
        
        # Count ranks and suits
        rank_counts = {}
        suit_counts = {}
        
        for card in cards:
            rank, suit = card[0], card[1]
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for pairs, trips, quads
        counts = sorted(rank_counts.values(), reverse=True)
        
        if counts[0] == 4:  # Four of a kind
            return 0.95
        elif counts[0] == 3 and counts[1] == 2:  # Full house
            return 0.9
        elif max(suit_counts.values()) >= 5:  # Flush
            return 0.8
        elif counts[0] == 3:  # Three of a kind
            return 0.7
        elif counts[0] == 2 and counts[1] == 2:  # Two pair
            return 0.6
        elif counts[0] == 2:  # One pair
            return 0.5
        else:  # High card
            return 0.3
    
    def _evaluate_made_hand_strength(self, all_cards, round_state: RoundStateClient):
        # Use basic hand strength with some adjustments
        base_strength = self._get_basic_hand_strength(all_cards)
        
        # Adjust based on board texture and our hole cards
        hole_contributes = self._hole_cards_contribute(all_cards)
        if hole_contributes:
            base_strength += 0.1
        
        return min(0.95, base_strength)
    
    def _hole_cards_contribute(self, all_cards):
        # Check if our hole cards contribute to the best hand
        community = [card for card in all_cards if card not in self.hole_cards]
        if len(community) < 3:
            return True
        
        # Simple check - if we have a pair with hole cards
        hole_ranks = [card[0] for card in self.hole_cards]
        community_ranks = [card[0] for card in community]
        
        for rank in hole_ranks:
            if rank in community_ranks:
                return True
        
        if hole_ranks[0] == hole_ranks[1]:  # Pocket pair
            return True
        
        return False
    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Track hand history for learning
        self.hand_history.append({
            'final_pot': round_state.pot,
            'final_chips': remaining_chips,
            'community_cards': round_state.community_cards.copy(),
            'hole_cards': self.hole_cards.copy()
        })
        
        # Keep only recent history to manage memory
        if len(self.hand_history) > 100:
            self.hand_history = self.hand_history[-50:]
    
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Learn from revealed hands if available
        if active_players_hands:
            for player_id, hand in active_players_hands.items():
                if int(player_id) != self.id and int(player_id) in self.player_stats:
                    # Could add hand strength analysis here
                    pass