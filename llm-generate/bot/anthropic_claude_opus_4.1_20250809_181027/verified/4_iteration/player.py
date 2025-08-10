from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 10000
        self.blind_amount = 10
        self.game_count = 0
        self.is_small_blind = False
        self.is_big_blind = False
        self.my_current_bet = 0
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.game_count += 1
        self.is_small_blind = (small_blind_player_id == self.id)
        self.is_big_blind = (big_blind_player_id == self.id)
        self.my_current_bet = 0
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Track our current bet in this betting round
        if str(self.id) in round_state.player_bets:
            self.my_current_bet = round_state.player_bets[str(self.id)]
        else:
            self.my_current_bet = 0
            
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Update our current bet
        if str(self.id) in round_state.player_bets:
            self.my_current_bet = round_state.player_bets[str(self.id)]
        else:
            self.my_current_bet = 0
            
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength(round_state)
        
        # Get basic info
        pot = round_state.pot
        current_bet = round_state.current_bet
        amount_to_call = max(0, current_bet - self.my_current_bet)
        
        # Calculate pot odds
        if amount_to_call > 0 and pot > 0:
            pot_odds = amount_to_call / (pot + amount_to_call + 0.001)
        else:
            pot_odds = 0
            
        # Preflop strategy
        if round_state.round == 'Preflop':
            # If we're small blind and facing just the big blind
            if self.is_small_blind and current_bet == self.blind_amount:
                # Complete the blind with any reasonable hand
                if hand_strength >= 0.3:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
            # Strong hands - raise or reraise
            if hand_strength >= 0.7:
                # Calculate valid raise amount
                min_raise_to = current_bet + round_state.min_raise
                raise_to = min(int(pot * 2 + current_bet), min_raise_to + 50, remaining_chips + self.my_current_bet)
                
                if raise_to > current_bet and (raise_to - self.my_current_bet) <= remaining_chips:
                    return (PokerAction.RAISE, raise_to)
                elif amount_to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
            # Medium hands - call if pot odds are good
            elif hand_strength >= 0.5:
                if amount_to_call == 0:
                    return (PokerAction.CHECK, 0)
                elif pot_odds < 0.3 and amount_to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
            # Weak hands
            else:
                if amount_to_call == 0:
                    return (PokerAction.CHECK, 0)
                elif amount_to_call <= self.blind_amount and pot >= self.blind_amount * 3:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
        # Postflop strategy
        else:
            # Very strong hands - bet/raise
            if hand_strength >= 0.8:
                if current_bet == 0:
                    # Bet
                    bet_amount = min(int(pot * 0.75), remaining_chips)
                    if bet_amount > 0:
                        return (PokerAction.RAISE, bet_amount)
                    else:
                        return (PokerAction.CHECK, 0)
                else:
                    # Raise if we can
                    min_raise_to = current_bet + round_state.min_raise
                    raise_to = min(current_bet * 2, remaining_chips + self.my_current_bet)
                    
                    if raise_to >= min_raise_to and (raise_to - self.my_current_bet) <= remaining_chips:
                        return (PokerAction.RAISE, raise_to)
                    elif amount_to_call <= remaining_chips:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                        
            # Good hands - call or small bet
            elif hand_strength >= 0.6:
                if amount_to_call == 0:
                    # Small bet
                    bet_amount = min(int(pot * 0.3), remaining_chips)
                    if bet_amount > 0 and bet_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, bet_amount)
                    else:
                        return (PokerAction.CHECK, 0)
                elif pot_odds < 0.35 and amount_to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
            # Weak hands
            else:
                if amount_to_call == 0:
                    return (PokerAction.CHECK, 0)
                elif pot_odds < 0.15 and amount_to_call <= remaining_chips * 0.1:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
    def _evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        """Evaluate hand strength from 0 to 1"""
        if not self.hole_cards or len(self.hole_cards) < 2:
            return 0.5
            
        # Parse hole cards
        card1, card2 = self.hole_cards[0], self.hole_cards[1]
        rank1, suit1 = self._parse_card(card1)
        rank2, suit2 = self._parse_card(card2)
        
        # Preflop hand strength
        if round_state.round == 'Preflop':
            # Pocket pairs
            if rank1 == rank2:
                if rank1 >= 12:  # QQ+
                    return 0.95
                elif rank1 >= 10:  # TT-JJ
                    return 0.85
                elif rank1 >= 7:  # 77-99
                    return 0.75
                else:  # 22-66
                    return 0.65
                    
            # High cards
            high = max(rank1, rank2)
            low = min(rank1, rank2)
            gap = high - low
            
            # Suited bonus
            suited_bonus = 0.05 if suit1 == suit2 else 0
            
            # AK, AQ
            if high == 14 and low >= 12:
                return 0.85 + suited_bonus
            # AJ, AT, KQ
            elif (high == 14 and low >= 10) or (high == 13 and low >= 12):
                return 0.75 + suited_bonus
            # Ax, KJ, QJ
            elif high == 14 or (high == 13 and low >= 11) or (high == 12 and low == 11):
                return 0.65 + suited_bonus
            # Connectors
            elif gap == 1 and high >= 10:
                return 0.6 + suited_bonus
            elif gap <= 2 and high >= 10:
                return 0.55 + suited_bonus
            # Two high cards
            elif high >= 10 and low >= 10:
                return 0.6
            elif high >= 10:
                return 0.5
            else:
                return 0.4 + suited_bonus
                
        # Postflop - simplified evaluation
        else:
            community = round_state.community_cards
            if not community:
                return 0.5
                
            # Check for pairs, trips, etc.
            all_ranks = [rank1, rank2] + [self._parse_card(c)[0] for c in community]
            rank_counts = {}
            for rank in all_ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
                
            max_count = max(rank_counts.values())
            
            # Check for flush potential
            all_suits = [suit1, suit2] + [self._parse_card(c)[1] for c in community]
            suit_counts = {}
            for suit in all_suits:
                suit_counts[suit] = suit_counts.get(suit, 0) + 1
            max_suit = max(suit_counts.values())
            
            # Rough hand evaluation
            if max_count >= 4:  # Four of a kind
                return 0.98
            elif max_count == 3 and len([c for c in rank_counts.values() if c >= 2]) >= 2:  # Full house
                return 0.95
            elif max_suit >= 5:  # Flush
                return 0.9
            elif max_count == 3:  # Three of a kind
                return 0.85
            elif len([c for c in rank_counts.values() if c >= 2]) >= 2:  # Two pair
                return 0.75
            elif max_count == 2:  # One pair
                # Check if we have the pair
                if rank_counts.get(rank1, 0) == 2 or rank_counts.get(rank2, 0) == 2:
                    return 0.65
                else:
                    return 0.55
            else:  # High card
                if max(rank1, rank2) >= 12:
                    return 0.45
                else:
                    return 0.35
                    
    def _parse_card(self, card: str) -> Tuple[int, str]:
        """Parse card string to rank (2-14) and suit"""
        if not card or len(card) < 2:
            return (2, 's')
            
        rank_str = card[0]
        suit = card[1]
        
        if rank_str == 'A':
            rank = 14
        elif rank_str == 'K':
            rank = 13
        elif rank_str == 'Q':
            rank = 12
        elif rank_str == 'J':
            rank = 11
        elif rank_str == 'T':
            rank = 10
        else:
            try:
                rank = int(rank_str)
            except:
                rank = 2
                
        return (rank, suit)
        
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        self.my_current_bet = 0
        
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass