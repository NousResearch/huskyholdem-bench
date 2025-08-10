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
        self.hand_count = 0
        self.opponent_stats = {}  # Track opponent tendencies
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player = big_blind_player_id
        self.small_blind_player = small_blind_player_id
        self.all_players = all_players
        self.hand_count += 1
        
        # Initialize opponent tracking
        for player_id in all_players:
            if player_id != self.id and player_id not in self.opponent_stats:
                self.opponent_stats[player_id] = {
                    'vpip': 0,  # Voluntarily put in pot
                    'pfr': 0,   # Pre-flop raise
                    'hands': 0,
                    'aggression': 0
                }

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Returns the action for the player."""
        
        # Calculate pot odds
        pot = round_state.pot
        to_call = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        pot_odds = to_call / (pot + to_call + 0.001) if to_call > 0 else 0
        
        # Get hand strength
        hand_strength = self._evaluate_hand_strength(round_state)
        
        # Position awareness
        is_in_position = self._is_in_position(round_state)
        
        # Stack size considerations
        stack_to_pot_ratio = remaining_chips / (pot + 0.001)
        
        # Decision making based on round
        if round_state.round == 'Preflop':
            return self._preflop_strategy(round_state, remaining_chips, hand_strength, is_in_position)
        else:
            return self._postflop_strategy(round_state, remaining_chips, hand_strength, pot_odds, is_in_position, stack_to_pot_ratio)

    def _preflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, hand_strength: float, is_in_position: bool) -> Tuple[PokerAction, int]:
        """Aggressive preflop strategy"""
        to_call = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        
        # Premium hands (AA, KK, QQ, AK)
        if hand_strength >= 0.85:
            if round_state.current_bet == 0:
                raise_amount = min(round_state.pot * 3, remaining_chips // 2)
                return (PokerAction.RAISE, raise_amount)
            elif to_call < remaining_chips * 0.3:
                raise_amount = min(to_call * 3, remaining_chips // 2)
                return (PokerAction.RAISE, raise_amount)
            else:
                return (PokerAction.ALL_IN, 0)
        
        # Strong hands (JJ, TT, AQ, AJ)
        elif hand_strength >= 0.70:
            if round_state.current_bet == 0:
                raise_amount = min(round_state.pot * 2.5, remaining_chips // 3)
                return (PokerAction.RAISE, raise_amount)
            elif to_call < remaining_chips * 0.15:
                if is_in_position:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.CALL, 0) if to_call < self.blind_amount * 3 else (PokerAction.FOLD, 0)
            else:
                return (PokerAction.FOLD, 0)
        
        # Medium hands (99-66, AT, KQ, suited connectors)
        elif hand_strength >= 0.50:
            if round_state.current_bet == 0:
                if is_in_position:
                    raise_amount = min(round_state.pot * 2, remaining_chips // 4)
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.CALL, 0) if to_call == 0 else (PokerAction.FOLD, 0)
            elif to_call < self.blind_amount * 2:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)
        
        # Weak hands
        else:
            if to_call == 0:
                return (PokerAction.CHECK, 0)
            elif to_call <= self.blind_amount and is_in_position:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)

    def _postflop_strategy(self, round_state: RoundStateClient, remaining_chips: int, hand_strength: float, pot_odds: float, is_in_position: bool, spr: float) -> Tuple[PokerAction, int]:
        """Aggressive postflop strategy"""
        to_call = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        pot = round_state.pot
        
        # Very strong hands (two pair or better)
        if hand_strength >= 0.80:
            if round_state.current_bet == 0:
                # Value bet
                bet_size = int(pot * 0.75)
                if bet_size < remaining_chips:
                    return (PokerAction.RAISE, bet_size)
                else:
                    return (PokerAction.ALL_IN, 0)
            else:
                # Re-raise for value
                if to_call < remaining_chips * 0.5:
                    raise_amount = min(to_call * 2.5, remaining_chips)
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.ALL_IN, 0)
        
        # Strong hands (top pair good kicker, overpair)
        elif hand_strength >= 0.65:
            if round_state.current_bet == 0:
                # Bet for value and protection
                bet_size = int(pot * 0.6)
                if bet_size < remaining_chips * 0.3:
                    return (PokerAction.RAISE, bet_size)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                # Call if pot odds are good
                if pot_odds < hand_strength * 0.8:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        
        # Medium hands (middle pair, weak top pair)
        elif hand_strength >= 0.45:
            if round_state.current_bet == 0:
                if is_in_position:
                    # Sometimes bet for thin value
                    if len(round_state.current_player) == 2:  # Heads up
                        bet_size = int(pot * 0.4)
                        if bet_size < remaining_chips * 0.2:
                            return (PokerAction.RAISE, bet_size)
                return (PokerAction.CHECK, 0)
            else:
                # Only call small bets
                if to_call < pot * 0.3 and pot_odds < hand_strength:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        
        # Draws and weak hands
        else:
            if round_state.current_bet == 0:
                # Occasional bluff in position
                if is_in_position and len(round_state.current_player) == 2:
                    if round_state.round == 'River' and pot < remaining_chips * 0.3:
                        # River bluff occasionally
                        if self.hand_count % 3 == 0:  # Bluff 1/3 of the time
                            bet_size = int(pot * 0.5)
                            return (PokerAction.RAISE, bet_size)
                return (PokerAction.CHECK, 0)
            else:
                # Fold to any bet
                return (PokerAction.FOLD, 0)

    def _evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        """Evaluate hand strength from 0 to 1"""
        if not self.hole_cards or len(self.hole_cards) != 2:
            return 0.3
        
        card1, card2 = self.hole_cards[0], self.hole_cards[1]
        rank1, rank2 = self._card_rank(card1), self._card_rank(card2)
        suited = card1[-1] == card2[-1]
        
        if round_state.round == 'Preflop':
            # Preflop hand strength evaluation
            strength = 0.0
            
            # Pocket pairs
            if rank1 == rank2:
                strength = 0.45 + (rank1 / 14) * 0.4  # 0.45 to 0.85 based on pair rank
            else:
                high_card = max(rank1, rank2)
                low_card = min(rank1, rank2)
                gap = high_card - low_card
                
                # High cards
                if high_card >= 12:  # Q or higher
                    strength = 0.35 + (high_card / 14) * 0.2
                    if low_card >= 10:  # Both broadway
                        strength += 0.15
                    if suited:
                        strength += 0.05
                    strength -= gap * 0.02  # Penalty for gaps
                # Suited connectors
                elif suited and gap <= 2:
                    strength = 0.30 + (high_card / 14) * 0.15
                # One high card
                elif high_card >= 10:
                    strength = 0.25 + (high_card / 14) * 0.1
                    if suited:
                        strength += 0.03
                else:
                    strength = 0.15 + (high_card / 14) * 0.1
                    if suited:
                        strength += 0.02
            
            return min(1.0, max(0.0, strength))
        
        else:
            # Postflop hand evaluation
            all_cards = self.hole_cards + round_state.community_cards
            strength = self._evaluate_postflop_hand(all_cards, round_state.community_cards)
            return strength

    def _evaluate_postflop_hand(self, all_cards: List[str], community: List[str]) -> float:
        """Evaluate postflop hand strength"""
        if not all_cards:
            return 0.3
            
        # Count ranks and suits
        ranks = {}
        suits = {}
        for card in all_cards:
            if card:
                rank = self._card_rank(card)
                suit = card[-1] if len(card) > 1 else ''
                ranks[rank] = ranks.get(rank, 0) + 1
                suits[suit] = suits.get(suit, 0) + 1
        
        # Check for various hand types
        rank_counts = sorted(ranks.values(), reverse=True)
        suit_counts = sorted(suits.values(), reverse=True)
        
        # Check for flush
        has_flush = suit_counts[0] >= 5 if suit_counts else False
        
        # Check for straight
        unique_ranks = sorted(ranks.keys())
        has_straight = self._check_straight(unique_ranks)
        
        # Determine hand strength
        if rank_counts[0] >= 4:  # Four of a kind
            return 0.95
        elif rank_counts[0] >= 3 and rank_counts[1] >= 2:  # Full house
            return 0.90
        elif has_flush:
            return 0.85
        elif has_straight:
            return 0.80
        elif rank_counts[0] >= 3:  # Three of a kind
            return 0.75
        elif rank_counts[0] >= 2 and rank_counts[1] >= 2:  # Two pair
            return 0.70
        elif rank_counts[0] >= 2:  # One pair
            # Adjust based on pair rank
            pair_rank = max([r for r, c in ranks.items() if c >= 2])
            # Check if we have top pair
            community_ranks = [self._card_rank(c) for c in community if c]
            if community_ranks and pair_rank >= max(community_ranks):
                return 0.65  # Top pair
            elif pair_rank >= 10:
                return 0.55  # Overpair or high pair
            else:
                return 0.45  # Lower pair
        else:
            # High card - evaluate based on rank
            high_card = max(ranks.keys()) if ranks else 2
            return 0.15 + (high_card / 14) * 0.2

    def _check_straight(self, ranks: List[int]) -> bool:
        """Check if we have a straight"""
        if len(ranks) < 5:
            return False
        
        # Check for regular straight
        for i in range(len(ranks) - 4):
            if ranks[i+4] - ranks[i] == 4:
                return True
        
        # Check for A-2-3-4-5 straight
        if 14 in ranks and set([2, 3, 4, 5]).issubset(set(ranks)):
            return True
            
        return False

    def _card_rank(self, card: str) -> int:
        """Convert card rank to numeric value"""
        if not card or len(card) < 2:
            return 2
        rank_char = card[0]
        if rank_char == 'A':
            return 14
        elif rank_char == 'K':
            return 13
        elif rank_char == 'Q':
            return 12
        elif rank_char == 'J':
            return 11
        elif rank_char == 'T':
            return 10
        else:
            try:
                return int(rank_char)
            except:
                return 2

    def _is_in_position(self, round_state: RoundStateClient) -> bool:
        """Check if we're in position (acting last)"""
        # In heads-up, small blind is in position postflop
        if len(self.all_players) == 2:
            if round_state.round == 'Preflop':
                return self.id == self.big_blind_player
            else:
                return self.id == self.small_blind_player
        else:
            # Multi-way: simplified - check if we're one of the last to act
            return True  # Simplified for now

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the end of the round."""
        # Update opponent stats based on their actions
        for player_id, action in round_state.player_actions.items():
            if player_id != str(self.id) and player_id in self.opponent_stats:
                if action in ['Raise', 'All_in']:
                    self.opponent_stats[player_id]['aggression'] += 1

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """Called at the end of the game."""
        pass