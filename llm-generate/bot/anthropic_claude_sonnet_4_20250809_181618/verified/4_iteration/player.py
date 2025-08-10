from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.big_blind_player = None
        self.small_blind_player = None
        self.all_players = []
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player = big_blind_player_id
        self.small_blind_player = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Get current bet we need to match
        my_current_bet = round_state.player_bets.get(str(self.id), 0)
        call_amount = max(0, round_state.current_bet - my_current_bet)
        
        # Calculate hand strength
        hand_strength = self._evaluate_hand_strength(self.hole_cards, round_state.community_cards, round_state.round)
        
        # Get pot odds
        pot_odds = self._calculate_pot_odds(round_state.pot, call_amount)
        
        # Make decision based on hand strength and pot odds
        action, amount = self._make_decision(hand_strength, pot_odds, call_amount, round_state, remaining_chips)
        
        return action, amount
    
    def _evaluate_hand_strength(self, hole_cards: List[str], community_cards: List[str], round_stage: str) -> float:
        """Evaluate hand strength on a scale of 0-1"""
        if not hole_cards or len(hole_cards) < 2:
            return 0.0
            
        card1, card2 = hole_cards[0], hole_cards[1]
        rank1, suit1 = self._parse_card(card1)
        rank2, suit2 = self._parse_card(card2)
        
        # Base strength from hole cards
        base_strength = 0.0
        
        # High pairs
        if rank1 == rank2:
            if rank1 >= 10:  # JJ, QQ, KK, AA
                base_strength = 0.85
            elif rank1 >= 7:  # 77, 88, 99, TT
                base_strength = 0.65
            else:  # 22-66
                base_strength = 0.45
        # High cards
        elif rank1 >= 12 or rank2 >= 12:  # Ace or King
            if rank1 >= 12 and rank2 >= 12:  # AK, AQ, KQ
                base_strength = 0.75
            elif (rank1 >= 12 and rank2 >= 10) or (rank2 >= 12 and rank1 >= 10):  # AJ, KJ, AT, KT
                base_strength = 0.55
            else:
                base_strength = 0.35
        # Suited connectors and mid pairs
        elif suit1 == suit2 or abs(rank1 - rank2) <= 2:
            base_strength = 0.4
        else:
            base_strength = 0.2
        
        # Adjust based on community cards if available
        if community_cards and len(community_cards) >= 3:
            all_cards = hole_cards + community_cards
            made_hand_strength = self._evaluate_made_hand(all_cards)
            base_strength = max(base_strength, made_hand_strength)
        
        return min(1.0, base_strength)
    
    def _parse_card(self, card: str) -> Tuple[int, str]:
        """Parse card string into rank (2-14) and suit"""
        if len(card) != 2:
            return 2, 's'
            
        rank_char = card[0]
        suit = card[1]
        
        if rank_char == 'A':
            rank = 14
        elif rank_char == 'K':
            rank = 13
        elif rank_char == 'Q':
            rank = 12
        elif rank_char == 'J':
            rank = 11
        elif rank_char == 'T':
            rank = 10
        else:
            try:
                rank = int(rank_char)
            except:
                rank = 2
                
        return rank, suit
    
    def _evaluate_made_hand(self, cards: List[str]) -> float:
        """Evaluate strength of made hand from all available cards"""
        if len(cards) < 5:
            return 0.3
            
        ranks = []
        suits = []
        
        for card in cards:
            rank, suit = self._parse_card(card)
            ranks.append(rank)
            suits.append(suit)
        
        rank_counts = {}
        suit_counts = {}
        
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for different hand types
        is_flush = max(suit_counts.values()) >= 5
        is_straight = self._has_straight(ranks)
        
        if is_straight and is_flush:
            return 0.95  # Straight flush
        elif 4 in rank_counts.values():
            return 0.9   # Four of a kind
        elif 3 in rank_counts.values() and 2 in rank_counts.values():
            return 0.85  # Full house
        elif is_flush:
            return 0.7   # Flush
        elif is_straight:
            return 0.65  # Straight
        elif 3 in rank_counts.values():
            return 0.5   # Three of a kind
        elif list(rank_counts.values()).count(2) >= 2:
            return 0.4   # Two pair
        elif 2 in rank_counts.values():
            return 0.25  # One pair
        else:
            return 0.15  # High card
    
    def _has_straight(self, ranks: List[int]) -> bool:
        """Check if ranks contain a straight"""
        unique_ranks = sorted(set(ranks))
        if len(unique_ranks) < 5:
            return False
            
        # Check for regular straight
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i+4] - unique_ranks[i] == 4:
                return True
        
        # Check for A-2-3-4-5 straight
        if 14 in unique_ranks and 2 in unique_ranks and 3 in unique_ranks and 4 in unique_ranks and 5 in unique_ranks:
            return True
            
        return False
    
    def _calculate_pot_odds(self, pot: int, call_amount: int) -> float:
        """Calculate pot odds"""
        if call_amount <= 0:
            return float('inf')
        return pot / (pot + call_amount + 0.001)  # Add small epsilon to avoid division by zero
    
    def _make_decision(self, hand_strength: float, pot_odds: float, call_amount: int, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Make the final decision based on all factors"""
        
        # If we can check (no bet to call), do it with weak hands
        if call_amount == 0:
            if hand_strength < 0.3:
                return PokerAction.CHECK, 0
            elif hand_strength > 0.7:
                # Bet with strong hands
                bet_size = min(round_state.pot // 2, remaining_chips // 4)
                if bet_size >= round_state.min_raise:
                    return PokerAction.RAISE, bet_size
                else:
                    return PokerAction.CHECK, 0
            else:
                return PokerAction.CHECK, 0
        
        # If there's a bet to call
        if call_amount > remaining_chips:
            # We can't afford to call, must fold or all-in
            if hand_strength > 0.8:
                return PokerAction.ALL_IN, 0
            else:
                return PokerAction.FOLD, 0
        
        # Decision matrix based on hand strength
        if hand_strength >= 0.8:
            # Very strong hand - raise or call
            if round_state.current_bet < round_state.pot // 2:
                # Calculate raise amount
                raise_amount = max(round_state.min_raise, min(round_state.pot // 2, remaining_chips // 3))
                if raise_amount <= round_state.max_raise and raise_amount >= round_state.min_raise:
                    return PokerAction.RAISE, raise_amount
            return PokerAction.CALL, 0
            
        elif hand_strength >= 0.6:
            # Strong hand - call or small raise
            if pot_odds > 0.3 or call_amount < round_state.pot // 4:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
                
        elif hand_strength >= 0.4:
            # Medium hand - call if pot odds are good
            if pot_odds > 0.4 and call_amount < round_state.pot // 3:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
                
        elif hand_strength >= 0.25:
            # Weak hand - only call with great pot odds
            if pot_odds > 0.6 and call_amount < round_state.pot // 5:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        else:
            # Very weak hand - fold
            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass