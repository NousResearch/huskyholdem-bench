from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 10000
        self.my_cards = []
        self.blind_amount = 10
        self.big_blind_player = None
        self.small_blind_player = None
        self.all_players = []
        self.opponent_history = {}
        self.game_history = []
        self.position_stats = {"early": [], "late": []}
        self.bluff_frequency = 0.15
        self.aggression_factor = 1.2

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.my_cards = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player = big_blind_player_id
        self.small_blind_player = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        if round_state.round == 'Preflop':
            hand_info = {
                'cards': self.my_cards,
                'position': 'late' if self.id == self.big_blind_player else 'early',
                'pot_odds': 0,
                'action_taken': None
            }
            self.game_history.append(hand_info)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            my_bet = round_state.player_bets.get(str(self.id), 0)
            amount_to_call = round_state.current_bet - my_bet
            
            # Calculate pot odds
            total_pot = round_state.pot + amount_to_call
            pot_odds = amount_to_call / (total_pot + 0.01) if total_pot > 0 else 0
            
            # Hand strength evaluation
            hand_strength = self._evaluate_hand_strength(round_state)
            position_factor = self._get_position_factor(round_state)
            
            # Opponent modeling
            opponent_aggression = self._estimate_opponent_aggression(round_state)
            
            # Bluff detection
            likely_bluff = self._detect_bluff_opportunity(round_state, hand_strength)
            
            # Stack management
            stack_ratio = remaining_chips / (self.starting_chips + 0.01)
            
            # Adjust strategy based on stack size
            if stack_ratio > 1.5:  # We're winning, play more aggressively
                self.aggression_factor = 1.4
                self.bluff_frequency = 0.20
            elif stack_ratio < 0.7:  # We're losing, tighten up
                self.aggression_factor = 0.9
                self.bluff_frequency = 0.08
            else:
                self.aggression_factor = 1.2
                self.bluff_frequency = 0.15
            
            # Decision making
            if round_state.current_bet == 0:
                # We can check
                if hand_strength >= 0.7 or (likely_bluff and hand_strength >= 0.4):
                    # Strong hand or good bluff spot - bet for value/bluff
                    bet_size = self._calculate_bet_size(round_state, hand_strength, remaining_chips)
                    if bet_size > 0 and bet_size <= remaining_chips:
                        return (PokerAction.RAISE, bet_size)
                return (PokerAction.CHECK, 0)
            
            else:
                # There's a bet to us
                if amount_to_call >= remaining_chips:
                    # All-in situation
                    if hand_strength >= 0.6 or pot_odds > 0.25:
                        return (PokerAction.ALL_IN, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                
                # Calculate expected value
                win_probability = self._calculate_win_probability(hand_strength, round_state)
                expected_value = (win_probability * total_pot) - (1 - win_probability) * amount_to_call
                
                # Consider position and opponent behavior
                adjusted_ev = expected_value * position_factor * (2 - opponent_aggression)
                
                if adjusted_ev > amount_to_call * 0.1:  # Positive EV threshold
                    if hand_strength >= 0.8 or (likely_bluff and remaining_chips > amount_to_call * 4):
                        # Strong hand or good bluff spot - raise
                        raise_size = self._calculate_raise_size(round_state, hand_strength, remaining_chips, amount_to_call)
                        if raise_size >= round_state.min_raise and raise_size <= remaining_chips:
                            return (PokerAction.RAISE, raise_size)
                    
                    # Good hand but not raise-worthy - call
                    if amount_to_call <= remaining_chips:
                        return (PokerAction.CALL, 0)
                
                # Marginal spots - consider pot odds and position
                if pot_odds < 0.3 and position_factor > 1.0 and hand_strength >= 0.3:
                    if amount_to_call <= remaining_chips:
                        return (PokerAction.CALL, 0)
                
                # Default to fold
                return (PokerAction.FOLD, 0)
                
        except Exception as e:
            # Emergency fallback
            if round_state.current_bet == 0:
                return (PokerAction.CHECK, 0)
            elif round_state.current_bet - round_state.player_bets.get(str(self.id), 0) <= remaining_chips // 10:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)

    def _evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        if not self.my_cards:
            return 0.3
        
        cards = self.my_cards[:]
        community = round_state.community_cards
        
        # Preflop hand strength
        if round_state.round == 'Preflop':
            return self._preflop_strength(cards)
        
        # Post-flop evaluation
        all_cards = cards + community
        return self._postflop_strength(all_cards, cards, community)
    
    def _preflop_strength(self, cards: List[str]) -> float:
        if len(cards) != 2:
            return 0.3
        
        card1, card2 = cards[0], cards[1]
        rank1, suit1 = card1[0], card1[1]
        rank2, suit2 = card2[0], card2[1]
        
        # Convert face cards to numbers
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 7)
        val2 = rank_values.get(rank2, 7)
        
        high_card = max(val1, val2)
        low_card = min(val1, val2)
        suited = (suit1 == suit2)
        paired = (val1 == val2)
        gap = high_card - low_card
        
        strength = 0.0
        
        # Pocket pairs
        if paired:
            if high_card >= 13:  # AA, KK
                strength = 0.95
            elif high_card >= 11:  # QQ, JJ
                strength = 0.85
            elif high_card >= 9:  # TT, 99
                strength = 0.75
            elif high_card >= 7:  # 88, 77
                strength = 0.65
            else:  # 66 and below
                strength = 0.55
        
        # High cards
        elif high_card == 14:  # Ace
            if low_card >= 12:  # AK, AQ
                strength = 0.80 if suited else 0.75
            elif low_card >= 10:  # AJ, AT
                strength = 0.70 if suited else 0.60
            elif low_card >= 8:  # A9, A8
                strength = 0.60 if suited else 0.45
            else:  # A7 and below
                strength = 0.50 if suited else 0.35
        
        elif high_card == 13:  # King
            if low_card >= 11:  # KQ, KJ
                strength = 0.70 if suited else 0.60
            elif low_card >= 9:  # KT, K9
                strength = 0.55 if suited else 0.45
            else:
                strength = 0.40 if suited else 0.30
        
        # Medium to low hands
        elif high_card >= 10:
            if gap <= 1 and low_card >= 9:  # Connected high cards
                strength = 0.60 if suited else 0.50
            elif gap <= 3 and suited:  # Suited connectors/gappers
                strength = 0.45
            else:
                strength = 0.35
        
        else:
            # Low cards
            if gap <= 1 and suited and low_card >= 6:  # Low suited connectors
                strength = 0.40
            else:
                strength = 0.25
        
        return min(0.99, max(0.05, strength))
    
    def _postflop_strength(self, all_cards: List[str], hole_cards: List[str], community: List[str]) -> float:
        if len(community) == 0:
            return self._preflop_strength(hole_cards)
        
        # Basic post-flop evaluation
        ranks = []
        suits = []
        
        for card in all_cards:
            if len(card) >= 2:
                rank = card[0]
                suit = card[1]
                rank_val = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                           '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}.get(rank, 7)
                ranks.append(rank_val)
                suits.append(suit)
        
        if len(ranks) < 2:
            return 0.3
        
        ranks.sort(reverse=True)
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        count_values = sorted(rank_counts.values(), reverse=True)
        max_suit_count = max(suit_counts.values()) if suit_counts else 0
        
        # Evaluate hand strength
        if count_values[0] == 4:  # Four of a kind
            return 0.95
        elif count_values[0] == 3 and count_values[1] == 2:  # Full house
            return 0.90
        elif max_suit_count >= 5:  # Flush
            return 0.85
        elif self._is_straight(ranks):  # Straight
            return 0.80
        elif count_values[0] == 3:  # Three of a kind
            return 0.75
        elif count_values[0] == 2 and count_values[1] == 2:  # Two pair
            return 0.65
        elif count_values[0] == 2:  # One pair
            pair_rank = max([rank for rank, count in rank_counts.items() if count == 2])
            if pair_rank >= 11:  # High pair
                return 0.60
            else:  # Low pair
                return 0.45
        else:  # High card
            if ranks[0] >= 12:  # King high or better
                return 0.40
            else:
                return 0.25
    
    def _is_straight(self, ranks: List[int]) -> bool:
        unique_ranks = sorted(list(set(ranks)), reverse=True)
        if len(unique_ranks) < 5:
            return False
        
        # Check for regular straight
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i] - unique_ranks[i+4] == 4:
                return True
        
        # Check for A-5 straight (wheel)
        if 14 in unique_ranks and 5 in unique_ranks and 4 in unique_ranks and 3 in unique_ranks and 2 in unique_ranks:
            return True
        
        return False
    
    def _get_position_factor(self, round_state: RoundStateClient) -> float:
        if len(self.all_players) <= 2:
            return 1.1 if self.id == self.big_blind_player else 0.95
        
        # In larger games, big blind is generally worse position preflop
        if round_state.round == 'Preflop':
            return 0.9 if self.id == self.big_blind_player else 1.1
        else:
            return 1.1 if self.id == self.big_blind_player else 0.95
    
    def _estimate_opponent_aggression(self, round_state: RoundStateClient) -> float:
        # Analyze opponent betting patterns
        total_actions = 0
        aggressive_actions = 0
        
        for player_id, action in round_state.player_actions.items():
            if player_id != str(self.id):
                total_actions += 1
                if action in ['Raise', 'All-in']:
                    aggressive_actions += 1
        
        if total_actions == 0:
            return 0.5  # Neutral assumption
        
        return min(1.0, aggressive_actions / (total_actions + 0.01))
    
    def _detect_bluff_opportunity(self, round_state: RoundStateClient, hand_strength: float) -> bool:
        # Simple bluff detection based on board texture and opponent behavior
        if len(round_state.community_cards) == 0:
            return False
        
        # More likely to bluff on dry boards with position
        position_factor = self._get_position_factor(round_state)
        opponent_aggression = self._estimate_opponent_aggression(round_state)
        
        # Bluff if we have position, opponent seems passive, and board is dry
        return (position_factor > 1.0 and 
                opponent_aggression < 0.3 and 
                hand_strength >= 0.2 and 
                hand_strength <= 0.5)
    
    def _calculate_win_probability(self, hand_strength: float, round_state: RoundStateClient) -> float:
        # Adjust win probability based on number of opponents and betting action
        base_prob = hand_strength
        
        # Adjust for number of active opponents
        active_opponents = len([p for p in round_state.current_player if p != self.id])
        opponent_factor = 0.9 ** active_opponents
        
        # Adjust for betting pressure (if there's heavy betting, we need stronger hands)
        betting_pressure = round_state.current_bet / (round_state.pot + 0.01)
        pressure_factor = 1.0 - min(0.3, betting_pressure * 0.5)
        
        return base_prob * opponent_factor * pressure_factor
    
    def _calculate_bet_size(self, round_state: RoundStateClient, hand_strength: float, remaining_chips: int) -> int:
        pot_size = round_state.pot
        
        if hand_strength >= 0.85:  # Very strong hand
            bet_size = int(pot_size * 0.8 * self.aggression_factor)
        elif hand_strength >= 0.65:  # Strong hand
            bet_size = int(pot_size * 0.6 * self.aggression_factor)
        elif hand_strength >= 0.45:  # Decent hand
            bet_size = int(pot_size * 0.4 * self.aggression_factor)
        else:  # Bluff or weak hand
            bet_size = int(pot_size * 0.3)
        
        return min(bet_size, remaining_chips, round_state.max_raise)
    
    def _calculate_raise_size(self, round_state: RoundStateClient, hand_strength: float, remaining_chips: int, amount_to_call: int) -> int:
        pot_size = round_state.pot + amount_to_call
        
        if hand_strength >= 0.85:  # Very strong hand
            raise_size = amount_to_call + int(pot_size * 0.8 * self.aggression_factor)
        elif hand_strength >= 0.65:  # Strong hand  
            raise_size = amount_to_call + int(pot_size * 0.6 * self.aggression_factor)
        else:  # Bluff
            raise_size = amount_to_call + int(pot_size * 0.4)
        
        # Ensure minimum raise
        min_total_bet = round_state.player_bets.get(str(self.id), 0) + round_state.min_raise
        raise_size = max(raise_size, min_total_bet - round_state.player_bets.get(str(self.id), 0))
        
        return min(raise_size, remaining_chips, round_state.max_raise)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update game history with results
        if self.game_history:
            self.game_history[-1]['final_pot'] = round_state.pot
            self.game_history[-1]['chips_after'] = remaining_chips

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Store game results for future analysis
        pass