from typing import List, Tuple, Dict
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hand = []
        self.starting_chips = 10000
        self.blind_amount = 0
        self.all_players = []
        self.hand_strength_cache = {}
        self.position_aggression_factor = 1.0
        self.opponent_stats = {}
        self.total_hands_played = 0
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hand = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.all_players = all_players
        self.hand_strength_cache = {}
        self.total_hands_played += 1
        
        # Initialize opponent tracking
        for player_id in all_players:
            if player_id not in self.opponent_stats:
                self.opponent_stats[player_id] = {
                    'vpip': 0,  # Voluntarily put money in pot
                    'pfr': 0,   # Pre-flop raise
                    'hands': 0,
                    'folds': 0,
                    'raises': 0,
                    'calls': 0
                }
    
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass
    
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Track opponent actions
        self._update_opponent_stats(round_state)
        
        # Calculate pot odds
        pot_odds = self._calculate_pot_odds(round_state, remaining_chips)
        
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength(round_state)
        
        # Get position-based aggression
        position_factor = self._get_position_factor(round_state)
        
        # Determine action based on game state
        if round_state.round == 'Preflop':
            return self._preflop_strategy(round_state, remaining_chips, hand_strength, pot_odds, position_factor)
        else:
            return self._postflop_strategy(round_state, remaining_chips, hand_strength, pot_odds, position_factor)
    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass
    
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass
    
    def _update_opponent_stats(self, round_state: RoundStateClient):
        for player_id, action in round_state.player_actions.items():
            if player_id == str(self.id):
                continue
            if player_id not in self.opponent_stats:
                self.opponent_stats[player_id] = {
                    'vpip': 0, 'pfr': 0, 'hands': 0, 'folds': 0, 'raises': 0, 'calls': 0
                }
            stats = self.opponent_stats[player_id]
            
            if action == 'Fold':
                stats['folds'] += 1
            elif action == 'Raise' or action == 'All-in':
                stats['raises'] += 1
            elif action == 'Call':
                stats['calls'] += 1
    
    def _calculate_pot_odds(self, round_state: RoundStateClient, remaining_chips: int):
        call_amount = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        if call_amount <= 0:
            return float('inf')
        
        total_pot = round_state.pot + call_amount
        return call_amount / (total_pot + 0.001)
    
    def _evaluate_hand_strength(self, round_state: RoundStateClient):
        # Cache key for performance
        cache_key = tuple(self.hand + round_state.community_cards)
        if cache_key in self.hand_strength_cache:
            return self.hand_strength_cache[cache_key]
        
        # Simplified hand strength evaluation
        strength = 0.0
        
        if round_state.round == 'Preflop':
            strength = self._preflop_hand_strength()
        else:
            strength = self._postflop_hand_strength(round_state.community_cards)
        
        self.hand_strength_cache[cache_key] = strength
        return strength
    
    def _preflop_hand_strength(self):
        if not self.hand or len(self.hand) < 2:
            return 0.2
            
        card1_rank = self._card_rank(self.hand[0])
        card2_rank = self._card_rank(self.hand[1])
        suited = self.hand[0][1] == self.hand[1][1]
        
        # Pocket pairs
        if card1_rank == card2_rank:
            if card1_rank >= 12:  # QQ+
                return 0.95
            elif card1_rank >= 10:  # TT-JJ
                return 0.85
            elif card1_rank >= 7:  # 77-99
                return 0.75
            else:
                return 0.65
        
        # High cards
        high_rank = max(card1_rank, card2_rank)
        low_rank = min(card1_rank, card2_rank)
        gap = high_rank - low_rank
        
        if high_rank == 14:  # Ace high
            if low_rank >= 11:  # AJ+
                return 0.85 if suited else 0.80
            elif low_rank >= 8:  # A8+
                return 0.70 if suited else 0.65
            else:
                return 0.55 if suited else 0.50
        
        if high_rank == 13:  # King high
            if low_rank >= 11:  # KJ+
                return 0.75 if suited else 0.70
            elif low_rank >= 9:  # K9+
                return 0.60 if suited else 0.55
            else:
                return 0.45 if suited else 0.40
        
        # Connected cards
        if gap == 1:
            return 0.60 if suited else 0.55
        elif gap == 2:
            return 0.50 if suited else 0.45
        
        # Default
        return 0.35 if suited else 0.30
    
    def _postflop_hand_strength(self, community_cards):
        all_cards = self.hand + community_cards
        
        # Check for made hands
        if self._has_flush(all_cards):
            return 0.90
        if self._has_straight(all_cards):
            return 0.85
        if self._has_three_of_kind(all_cards):
            return 0.80
        if self._has_two_pair(all_cards):
            return 0.70
        if self._has_pair(all_cards):
            return 0.55
        
        # High card
        return 0.30
    
    def _get_position_factor(self, round_state: RoundStateClient):
        num_players = len(round_state.current_player)
        if num_players <= 2:
            return 1.2
        
        # Estimate position based on betting order
        if len(round_state.player_actions) < num_players // 2:
            return 0.9  # Early position
        else:
            return 1.1  # Late position
    
    def _preflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, hand_strength: float, pot_odds: float, position_factor: float):
        my_bet = round_state.player_bets.get(str(self.id), 0)
        call_amount = round_state.current_bet - my_bet
        
        # Adjust strength based on position
        adjusted_strength = hand_strength * position_factor
        
        # Premium hands - always raise
        if adjusted_strength >= 0.90:
            if remaining_chips <= round_state.pot * 2:
                return (PokerAction.ALL_IN, 0)
            raise_amount = min(round_state.pot * 3, remaining_chips // 2)
            if raise_amount > round_state.min_raise:
                return (PokerAction.RAISE, raise_amount)
            elif call_amount > 0:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.CHECK, 0)
        
        # Strong hands
        if adjusted_strength >= 0.70:
            if call_amount <= remaining_chips * 0.15:
                if random.random() < 0.6:
                    raise_amount = min(round_state.pot * 2, remaining_chips // 3)
                    if raise_amount > round_state.min_raise:
                        return (PokerAction.RAISE, raise_amount)
                if call_amount > 0:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.CHECK, 0)
            elif pot_odds < adjusted_strength - 0.2:
                return (PokerAction.CALL, 0)
        
        # Medium hands
        if adjusted_strength >= 0.50:
            if call_amount <= self.blind_amount * 3:
                if call_amount > 0:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.CHECK, 0)
        
        # Weak hands
        if call_amount == 0:
            return (PokerAction.CHECK, 0)
        else:
            return (PokerAction.FOLD, 0)
    
    def _postflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, hand_strength: float, pot_odds: float, position_factor: float):
        my_bet = round_state.player_bets.get(str(self.id), 0)
        call_amount = round_state.current_bet - my_bet
        
        # Adjust based on pot size and stack
        pot_to_stack = round_state.pot / (remaining_chips + 0.001)
        
        # Very strong hands
        if hand_strength >= 0.85:
            if pot_to_stack > 0.5 or remaining_chips < round_state.pot:
                return (PokerAction.ALL_IN, 0)
            
            raise_amount = min(round_state.pot * 0.75, remaining_chips // 2)
            if raise_amount > round_state.min_raise:
                return (PokerAction.RAISE, raise_amount)
            elif call_amount > 0:
                return (PokerAction.CALL, 0)
            else:
                # Value bet
                bet_amount = round_state.pot // 2
                if bet_amount > round_state.min_raise:
                    return (PokerAction.RAISE, bet_amount)
                return (PokerAction.CHECK, 0)
        
        # Good hands
        if hand_strength >= 0.60:
            if pot_odds < hand_strength - 0.3:
                if call_amount > 0:
                    return (PokerAction.CALL, 0)
                else:
                    # Small value bet
                    bet_amount = round_state.pot // 3
                    if bet_amount > round_state.min_raise and random.random() < 0.4:
                        return (PokerAction.RAISE, bet_amount)
                    return (PokerAction.CHECK, 0)
        
        # Drawing hands or marginal
        if hand_strength >= 0.40:
            if call_amount == 0:
                return (PokerAction.CHECK, 0)
            elif pot_odds < 0.2:
                return (PokerAction.CALL, 0)
        
        # Weak hands
        if call_amount == 0:
            return (PokerAction.CHECK, 0)
        else:
            return (PokerAction.FOLD, 0)
    
    def _card_rank(self, card):
        if not card or len(card) < 1:
            return 2
        rank = card[0]
        if rank == 'A':
            return 14
        elif rank == 'K':
            return 13
        elif rank == 'Q':
            return 12
        elif rank == 'J':
            return 11
        elif rank == 'T':
            return 10
        else:
            try:
                return int(rank)
            except:
                return 2
    
    def _has_flush(self, cards):
        suits = {}
        for card in cards:
            if len(card) >= 2:
                suit = card[1]
                suits[suit] = suits.get(suit, 0) + 1
                if suits[suit] >= 5:
                    return True
        return False
    
    def _has_straight(self, cards):
        ranks = set()
        for card in cards:
            ranks.add(self._card_rank(card))
        
        ranks = sorted(ranks)
        if len(ranks) < 5:
            return False
        
        for i in range(len(ranks) - 4):
            if ranks[i+4] - ranks[i] == 4:
                return True
        
        # Check A-2-3-4-5
        if 14 in ranks and set([2, 3, 4, 5]).issubset(ranks):
            return True
        
        return False
    
    def _has_three_of_kind(self, cards):
        ranks = {}
        for card in cards:
            rank = self._card_rank(card)
            ranks[rank] = ranks.get(rank, 0) + 1
            if ranks[rank] >= 3:
                return True
        return False
    
    def _has_two_pair(self, cards):
        ranks = {}
        for card in cards:
            rank = self._card_rank(card)
            ranks[rank] = ranks.get(rank, 0) + 1
        
        pairs = sum(1 for count in ranks.values() if count >= 2)
        return pairs >= 2
    
    def _has_pair(self, cards):
        ranks = {}
        for card in cards:
            rank = self._card_rank(card)
            ranks[rank] = ranks.get(rank, 0) + 1
            if ranks[rank] >= 2:
                return True
        return False