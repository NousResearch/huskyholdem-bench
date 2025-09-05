from typing import List, Tuple
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
        self.big_blind_player = None
        self.small_blind_player = None
        self.all_players = []
        self.game_count = 0
        self.aggression_factor = 0.3
        self.bluff_frequency = 0.15
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, 
                 big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player = big_blind_player_id
        self.small_blind_player = small_blind_player_id
        self.all_players = all_players
        self.game_count += 1
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Returns the action for the player."""
        
        # Safety check for chips
        if remaining_chips <= 0:
            return (PokerAction.FOLD, 0)
            
        # Calculate pot odds and implied odds
        pot = round_state.pot
        to_call = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        pot_odds = to_call / (pot + to_call + 0.001) if to_call > 0 else 0
        
        # Get position information
        is_button = self.is_button_position(round_state)
        is_big_blind = (self.id == self.big_blind_player)
        num_players = len(round_state.current_player)
        
        # Evaluate hand strength
        hand_strength = self.evaluate_hand_strength(round_state)
        
        # Adjust strategy based on position
        position_multiplier = 1.3 if is_button else 1.0
        hand_strength *= position_multiplier
        
        # Preflop strategy - be more aggressive
        if round_state.round == 'Preflop':
            return self.get_preflop_action(round_state, remaining_chips, hand_strength, 
                                          pot_odds, is_big_blind, num_players)
        
        # Postflop strategy
        return self.get_postflop_action(round_state, remaining_chips, hand_strength, 
                                       pot_odds, to_call, pot)
        
    def get_preflop_action(self, round_state, remaining_chips, hand_strength, 
                          pot_odds, is_big_blind, num_players):
        """Preflop action logic - more aggressive to avoid folding too much"""
        
        to_call = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        
        # Premium hands - always raise or reraise
        if hand_strength > 0.85:
            if round_state.current_bet > self.blind_amount * 2:
                # 3-bet or 4-bet
                raise_amount = min(round_state.current_bet * 3, remaining_chips)
                if raise_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, raise_amount)
            else:
                # Open raise
                raise_amount = min(self.blind_amount * 3, remaining_chips)
                if raise_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, raise_amount)
                    
        # Good hands - raise or call
        if hand_strength > 0.65:
            if round_state.current_bet <= self.blind_amount * 3:
                raise_amount = min(round_state.current_bet * 2 + self.blind_amount, remaining_chips)
                if raise_amount >= round_state.min_raise and random.random() < 0.6:
                    return (PokerAction.RAISE, raise_amount)
            if to_call <= remaining_chips:
                return (PokerAction.CALL, 0)
                
        # Decent hands - call small bets or check
        if hand_strength > 0.45:
            if to_call <= self.blind_amount * 2 and to_call <= remaining_chips:
                return (PokerAction.CALL, 0)
            elif to_call == 0:
                # Occasionally raise as a bluff
                if random.random() < self.bluff_frequency:
                    raise_amount = min(self.blind_amount * 2, remaining_chips)
                    if raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, raise_amount)
                return (PokerAction.CHECK, 0)
                
        # Marginal hands - defend big blind or fold
        if is_big_blind and to_call <= self.blind_amount:
            # Defend big blind with wider range
            if hand_strength > 0.25 or random.random() < 0.3:
                if to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                    
        # Weak hands but consider position and pot odds
        if to_call == 0:
            return (PokerAction.CHECK, 0)
        elif pot_odds < 0.2 and hand_strength > 0.3:
            if to_call <= remaining_chips:
                return (PokerAction.CALL, 0)
        
        # Occasional bluff to balance range
        if random.random() < self.bluff_frequency * 0.5:
            if to_call <= self.blind_amount and to_call <= remaining_chips:
                return (PokerAction.CALL, 0)
                
        return (PokerAction.FOLD, 0)
        
    def get_postflop_action(self, round_state, remaining_chips, hand_strength, 
                           pot_odds, to_call, pot):
        """Postflop action logic"""
        
        # Very strong hands - bet/raise aggressively
        if hand_strength > 0.8:
            if to_call > 0:
                raise_amount = min(to_call * 2 + pot // 2, remaining_chips)
                if raise_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, raise_amount)
                return (PokerAction.CALL, 0) if to_call <= remaining_chips else (PokerAction.FOLD, 0)
            else:
                # Bet for value
                bet_amount = min(pot * 2 // 3, remaining_chips)
                if bet_amount >= round_state.min_raise:
                    return (PokerAction.RAISE, bet_amount)
                    
        # Good hands - bet/call
        if hand_strength > 0.6:
            if to_call > 0:
                if pot_odds < 0.3 and to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
            else:
                # Continuation bet
                bet_amount = min(pot // 2, remaining_chips)
                if bet_amount >= round_state.min_raise and random.random() < 0.7:
                    return (PokerAction.RAISE, bet_amount)
                return (PokerAction.CHECK, 0)
                
        # Drawing hands or marginal made hands
        if hand_strength > 0.4:
            if to_call > 0:
                if pot_odds < 0.25 and to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
            else:
                # Semi-bluff occasionally
                if random.random() < self.bluff_frequency:
                    bet_amount = min(pot // 3, remaining_chips)
                    if bet_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, bet_amount)
                return (PokerAction.CHECK, 0)
                
        # Weak hands
        if to_call == 0:
            return (PokerAction.CHECK, 0)
        elif pot_odds < 0.15 and hand_strength > 0.25:
            if to_call <= remaining_chips * 0.1:  # Only call very small bets
                return (PokerAction.CALL, 0)
                
        return (PokerAction.FOLD, 0)
        
    def evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        """Evaluate hand strength from 0 to 1"""
        
        if not self.hole_cards or len(self.hole_cards) < 2:
            return 0.3
            
        card1, card2 = self.hole_cards[0], self.hole_cards[1]
        rank1, rank2 = self.get_card_rank(card1), self.get_card_rank(card2)
        suited = card1[-1] == card2[-1]
        
        # Preflop hand strength
        if round_state.round == 'Preflop':
            # Pocket pairs
            if rank1 == rank2:
                if rank1 >= 12:  # AA, KK, QQ
                    return 0.95
                elif rank1 >= 10:  # JJ, TT
                    return 0.85
                elif rank1 >= 8:  # 99, 88
                    return 0.75
                elif rank1 >= 6:  # 77, 66
                    return 0.65
                else:  # Small pairs
                    return 0.55
                    
            # High cards
            max_rank = max(rank1, rank2)
            min_rank = min(rank1, rank2)
            gap = max_rank - min_rank
            
            if max_rank == 14:  # Ace high
                if min_rank >= 11:  # AK, AQ, AJ
                    return 0.85 if suited else 0.80
                elif min_rank >= 9:  # AT, A9
                    return 0.70 if suited else 0.65
                else:
                    return 0.55 if suited else 0.45
                    
            elif max_rank == 13:  # King high
                if min_rank >= 11:  # KQ, KJ
                    return 0.75 if suited else 0.70
                elif min_rank >= 9:  # KT, K9
                    return 0.60 if suited else 0.55
                else:
                    return 0.45 if suited else 0.35
                    
            elif max_rank >= 11:  # Queen or Jack high
                if gap <= 2:  # Connected cards
                    return 0.65 if suited else 0.55
                else:
                    return 0.50 if suited else 0.40
                    
            # Suited connectors
            if suited and gap == 1:
                return 0.55 + (min_rank * 0.02)
                
            # Other hands
            return 0.35 + (max_rank * 0.015)
            
        # Postflop - simplified evaluation
        else:
            community = round_state.community_cards
            if not community:
                return 0.5
                
            # Check for pairs, sets, etc.
            all_cards = self.hole_cards + community
            ranks = [self.get_card_rank(c) for c in all_cards]
            rank_counts = {}
            for r in ranks:
                rank_counts[r] = rank_counts.get(r, 0) + 1
                
            max_count = max(rank_counts.values())
            
            if max_count >= 4:  # Four of a kind
                return 0.95
            elif max_count == 3:  # Three of a kind
                if len([c for c in rank_counts.values() if c >= 2]) >= 2:  # Full house
                    return 0.90
                return 0.75
            elif max_count == 2:  # Pair
                pairs = [r for r, c in rank_counts.items() if c == 2]
                if len(pairs) >= 2:  # Two pair
                    return 0.65
                elif max(pairs) in [self.get_card_rank(self.hole_cards[0]), 
                                   self.get_card_rank(self.hole_cards[1])]:
                    # Pair with hole card
                    return 0.55
                else:
                    return 0.45
                    
            # High card
            return 0.35 + (max(ranks) / 14) * 0.2
            
    def get_card_rank(self, card: str) -> int:
        """Convert card rank to numerical value"""
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
                
    def is_button_position(self, round_state: RoundStateClient) -> bool:
        """Check if we're in late position (button or cutoff)"""
        if not self.all_players or len(self.all_players) < 2:
            return False
        try:
            my_index = self.all_players.index(self.id)
            total_players = len(self.all_players)
            # Consider last 2 positions as late position
            return my_index >= total_players - 2
        except:
            return False
            
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the end of the round."""
        pass
        
    def on_end_game(self, round_state: RoundStateClient, player_score: float, 
                    all_scores: dict, active_players_hands: dict):
        """Called at the end of the game."""
        # Adjust aggression based on performance
        if player_score > 0:
            self.aggression_factor = min(0.5, self.aggression_factor + 0.02)
        elif player_score < -50:
            self.aggression_factor = max(0.2, self.aggression_factor - 0.02)