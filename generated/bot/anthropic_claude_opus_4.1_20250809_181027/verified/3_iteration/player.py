from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.folded = False
        self.game_count = 0
        self.total_games = 0
        self.current_round = None
        self.blind_amount = 10
        self.is_small_blind = False
        self.is_big_blind = False
        self.my_current_bet = 0
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.folded = False
        self.game_count += 1
        self.blind_amount = blind_amount
        self.is_big_blind = (self.id == big_blind_player_id)
        self.is_small_blind = (self.id == small_blind_player_id)
        self.my_current_bet = 0
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.current_round = round_state.round
        self.my_current_bet = round_state.player_bets.get(str(self.id), 0)
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Returns the action for the player."""
        # Update my current bet
        self.my_current_bet = round_state.player_bets.get(str(self.id), 0)
        
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength()
        
        # Get pot odds
        pot = round_state.pot
        to_call = round_state.current_bet - self.my_current_bet
        
        # Calculate pot odds
        if to_call > 0:
            pot_odds = to_call / (pot + to_call + 0.001)  # Avoid division by zero
        else:
            pot_odds = 0
            
        # Decision logic based on position and hand strength
        is_preflop = (round_state.round == 'Preflop')
        
        # If we need to call
        if to_call > 0:
            # Strong hands - raise or call
            if hand_strength >= 0.8:
                # Calculate a valid raise amount
                min_raise = round_state.min_raise
                max_raise = min(round_state.max_raise, remaining_chips)
                
                if min_raise <= max_raise and min_raise > 0:
                    # Make sure our raise is valid
                    raise_amount = min(max(min_raise, pot // 2), max_raise)
                    if raise_amount > 0 and raise_amount >= min_raise:
                        return (PokerAction.RAISE, raise_amount)
                
                # If we can't raise properly, just call
                if to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.ALL_IN, 0)
                    
            # Medium hands - call if pot odds are good
            elif hand_strength >= 0.5:
                if pot_odds < 0.4 or (is_preflop and hand_strength >= 0.6):
                    if to_call <= remaining_chips:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.ALL_IN, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
            # Weak hands - fold unless pot odds are excellent
            else:
                if pot_odds < 0.2 and pot > 50:
                    if to_call <= remaining_chips:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                else:
                    return (PokerAction.FOLD, 0)
        
        # If we don't need to call (current_bet == 0 or we've matched it)
        else:
            # Strong hands - bet/raise
            if hand_strength >= 0.75:
                min_raise = round_state.min_raise
                max_raise = min(round_state.max_raise, remaining_chips)
                
                # Only raise if we can make a valid raise
                if min_raise <= max_raise and min_raise > 0:
                    raise_amount = min(max(min_raise, pot // 3), max_raise)
                    if raise_amount > 0 and raise_amount >= min_raise:
                        return (PokerAction.RAISE, raise_amount)
                
                # Otherwise just check
                return (PokerAction.CHECK, 0)
                
            # Medium hands - check
            elif hand_strength >= 0.4:
                return (PokerAction.CHECK, 0)
                
            # Weak hands - check (free card)
            else:
                return (PokerAction.CHECK, 0)
    
    def _evaluate_hand_strength(self) -> float:
        """Evaluate hand strength (0-1 scale)"""
        if not self.hole_cards or len(self.hole_cards) < 2:
            return 0.3
            
        card1 = self.hole_cards[0]
        card2 = self.hole_cards[1]
        
        rank1 = self._card_rank(card1)
        rank2 = self._card_rank(card2)
        
        is_suited = (card1[-1] == card2[-1])
        is_pair = (rank1 == rank2)
        
        high_rank = max(rank1, rank2)
        low_rank = min(rank1, rank2)
        gap = high_rank - low_rank
        
        # Base strength from high card
        strength = high_rank / 14.0
        
        # Bonuses
        if is_pair:
            strength += 0.3 + (rank1 / 14.0) * 0.2  # Pairs are strong
        
        if is_suited:
            strength += 0.1  # Suited bonus
            
        if gap <= 1 and not is_pair:  # Connectors
            strength += 0.05
            
        if high_rank >= 10:  # High cards bonus
            strength += 0.1
            
        if high_rank >= 12 and low_rank >= 10:  # Both high cards
            strength += 0.15
            
        # Cap at 1.0
        return min(strength, 1.0)
    
    def _card_rank(self, card: str) -> int:
        """Convert card rank to numerical value"""
        rank = card[:-1]  # Remove suit
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
            return int(rank)
    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the end of the round."""
        pass
    
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """Called at the end of the game."""
        self.total_games += 1