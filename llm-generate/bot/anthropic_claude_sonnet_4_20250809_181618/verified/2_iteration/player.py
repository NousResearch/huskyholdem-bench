from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.opponent_tendencies = {"aggressive": 0, "passive": 0}
        self.game_phase = "early"  # early, mid, late
        self.hands_played = 0
        self.starting_chips = 10000
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.hands_played = 0
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.hands_played += 1
        # Update game phase based on hands played
        if self.hands_played < 10:
            self.game_phase = "early"
        elif self.hands_played < 25:
            self.game_phase = "mid"
        else:
            self.game_phase = "late"

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # Get hand strength
        hand_strength = self._evaluate_hand_strength(self.hole_cards, round_state.community_cards)
        
        # Calculate pot odds and betting context
        call_amount = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
        pot_odds = call_amount / max(1, round_state.pot + call_amount) if call_amount > 0 else 0
        
        # Position and aggression analysis
        is_aggressive_situation = self._should_be_aggressive(round_state, remaining_chips)
        
        # Decision logic based on hand strength and situation
        if hand_strength >= 0.8:  # Very strong hand
            if round_state.current_bet == 0:
                # Bet for value
                bet_size = min(round_state.pot // 2 + round_state.min_raise, remaining_chips)
                if bet_size >= round_state.min_raise:
                    return (PokerAction.RAISE, bet_size)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                # Raise or call
                if is_aggressive_situation and remaining_chips > round_state.min_raise + call_amount:
                    raise_size = min(round_state.pot // 3 + call_amount + round_state.min_raise, remaining_chips)
                    return (PokerAction.RAISE, raise_size)
                else:
                    return (PokerAction.CALL, 0)
                    
        elif hand_strength >= 0.6:  # Good hand
            if round_state.current_bet == 0:
                # Sometimes bet, sometimes check
                if is_aggressive_situation:
                    bet_size = min(round_state.pot // 3 + round_state.min_raise, remaining_chips)
                    if bet_size >= round_state.min_raise:
                        return (PokerAction.RAISE, bet_size)
                return (PokerAction.CHECK, 0)
            else:
                # Call if pot odds are reasonable
                if pot_odds < 0.4 or call_amount <= remaining_chips // 4:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
        elif hand_strength >= 0.4:  # Marginal hand
            if round_state.current_bet == 0:
                return (PokerAction.CHECK, 0)
            else:
                # Call small bets, fold to large bets
                if pot_odds < 0.25 and call_amount <= remaining_chips // 8:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
        else:  # Weak hand
            if round_state.current_bet == 0:
                # Occasionally bluff in late position
                if (is_aggressive_situation and round_state.round in ["Turn", "River"] and 
                    len(round_state.current_player) <= 2):
                    bet_size = min(round_state.pot // 4 + round_state.min_raise, remaining_chips // 3)
                    if bet_size >= round_state.min_raise:
                        return (PokerAction.RAISE, bet_size)
                return (PokerAction.CHECK, 0)
            else:
                return (PokerAction.FOLD, 0)

    def _evaluate_hand_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        """Evaluate hand strength from 0.0 to 1.0"""
        if not hole_cards or len(hole_cards) < 2:
            return 0.3
            
        # Parse cards
        card1_rank, card1_suit = self._parse_card(hole_cards[0])
        card2_rank, card2_suit = self._parse_card(hole_cards[1])
        
        strength = 0.0
        
        # Pocket pair bonus
        if card1_rank == card2_rank:
            if card1_rank >= 10:  # High pairs
                strength += 0.7
            elif card1_rank >= 7:  # Medium pairs
                strength += 0.5
            else:  # Low pairs
                strength += 0.3
        else:
            # High card strength
            high_card = max(card1_rank, card2_rank)
            low_card = min(card1_rank, card2_rank)
            
            if high_card == 14:  # Ace
                strength += 0.4
            elif high_card >= 11:  # Face cards
                strength += 0.3
            elif high_card >= 8:
                strength += 0.2
            else:
                strength += 0.1
                
            # Second card bonus
            if low_card >= 10:
                strength += 0.2
            elif low_card >= 7:
                strength += 0.1
                
        # Suited bonus
        if card1_suit == card2_suit:
            strength += 0.1
            
        # Connected cards bonus
        if abs(card1_rank - card2_rank) == 1:
            strength += 0.1
        elif abs(card1_rank - card2_rank) <= 3:
            strength += 0.05
            
        # Community cards consideration
        if community_cards:
            strength += self._evaluate_post_flop_strength(hole_cards, community_cards)
            
        return min(1.0, strength)

    def _evaluate_post_flop_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        """Additional strength evaluation with community cards"""
        if not community_cards:
            return 0.0
            
        all_cards = hole_cards + community_cards
        
        # Count ranks and suits
        ranks = {}
        suits = {}
        for card in all_cards:
            rank, suit = self._parse_card(card)
            ranks[rank] = ranks.get(rank, 0) + 1
            suits[suit] = suits.get(suit, 0) + 1
            
        strength_bonus = 0.0
        
        # Check for pairs, trips, etc.
        rank_counts = list(ranks.values())
        rank_counts.sort(reverse=True)
        
        if rank_counts[0] >= 4:  # Four of a kind
            strength_bonus += 0.8
        elif rank_counts[0] >= 3:  # Three of a kind
            strength_bonus += 0.5
            if len(rank_counts) > 1 and rank_counts[1] >= 2:  # Full house
                strength_bonus += 0.3
        elif rank_counts[0] >= 2:  # Pair
            strength_bonus += 0.2
            if len(rank_counts) > 1 and rank_counts[1] >= 2:  # Two pair
                strength_bonus += 0.2
                
        # Check for flush potential
        max_suit_count = max(suits.values()) if suits else 0
        if max_suit_count >= 5:  # Flush
            strength_bonus += 0.6
        elif max_suit_count >= 4:  # Flush draw
            strength_bonus += 0.1
            
        # Check for straight potential
        sorted_ranks = sorted(set(ranks.keys()))
        if len(sorted_ranks) >= 5:
            for i in range(len(sorted_ranks) - 4):
                if sorted_ranks[i+4] - sorted_ranks[i] == 4:  # Straight
                    strength_bonus += 0.5
                    break
                    
        return min(0.5, strength_bonus)

    def _parse_card(self, card: str) -> Tuple[int, str]:
        """Parse card string into rank and suit"""
        if len(card) < 2:
            return (2, 'h')  # Default fallback
            
        rank_char = card[0]
        suit = card[1]
        
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        rank = rank_map.get(rank_char, 2)
        return (rank, suit)

    def _should_be_aggressive(self, round_state: RoundStateClient, remaining_chips: int) -> bool:
        """Determine if we should play aggressively"""
        # Be more aggressive when:
        # 1. We have good chip position
        # 2. Pot is small relative to remaining chips
        # 3. Few players in hand
        # 4. Late in game with short stack
        
        chip_ratio = remaining_chips / max(1, self.starting_chips)
        pot_to_chips_ratio = round_state.pot / max(1, remaining_chips)
        
        aggression_factors = 0
        
        # Chip position
        if chip_ratio > 1.2:  # Winning
            aggression_factors += 1
        elif chip_ratio < 0.6:  # Short stack
            aggression_factors += 1
            
        # Pot size
        if pot_to_chips_ratio < 0.1:  # Small pot
            aggression_factors += 1
            
        # Player count
        if len(round_state.current_player) <= 2:
            aggression_factors += 1
            
        # Game phase
        if self.game_phase == "late":
            aggression_factors += 1
            
        return aggression_factors >= 2

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update opponent tendency tracking
        for player_id, action in round_state.player_actions.items():
            if player_id != str(self.id):
                if action in ["RAISE", "ALL_IN"]:
                    self.opponent_tendencies["aggressive"] += 1
                elif action in ["CHECK", "CALL"]:
                    self.opponent_tendencies["passive"] += 1

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Reset for next game
        self.opponent_tendencies = {"aggressive": 0, "passive": 0}
        self.hands_played = 0