from typing import List, Tuple, Dict, Any
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from collections import defaultdict
import itertools

# Hand category constants
HIGH_CARD = 1
ONE_PAIR = 2
TWO_PAIR = 3
THREE_OF_A_KIND = 4
STRAIGHT = 5
FLUSH = 6
FULL_HOUSE = 7
FOUR_OF_A_KIND = 8
STRAIGHT_FLUSH = 9
ROYAL_FLUSH = 10

# Mapping for card ranks
RANK_TO_VALUE = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
}

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.big_blind_amount = 0
        self.hole_cards = []
        self.remaining_chips = 0
        self.stage_factor = 0
        self.player_position = 0
        self.hand_strength_cache = {}
        self.preflop_open_raise_amount = 0
        self.active_players = 0

    def _convert_card(self, card: str) -> Tuple[int, str]:
        """Convert card string to (value, suit) tuple."""
        rank = card[:-1]
        suit = card[-1]
        return RANK_TO_VALUE.get(rank, 2), suit

    def _eval_hand_category_of_5(self, cards: List[Tuple[int, str]]) -> int:
        """Evaluate hand category for 5 cards."""
        ranks = sorted([c[0] for c in cards], reverse=True)
        suits = [c[1] for c in cards]
        
        # Check flush
        is_flush = len(set(suits)) == 1
        
        # Check straight
        is_straight = True
        for i in range(1, 5):
            if ranks[0] - ranks[i] != i:
                is_straight = False
                break
        
        if is_flush and is_straight:
            return STRAIGHT_FLUSH
        if is_flush and ranks == [14, 13, 12, 11, 10]:
            return ROYAL_FLUSH
        
        # Count ranks
        rank_counts = defaultdict(int)
        for rank in ranks:
            rank_counts[rank] += 1
        
        sorted_rank_counts = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        
        if sorted_rank_counts[0][1] == 4:
            return FOUR_OF_A_KIND
        if sorted_rank_counts[0][1] == 3 and sorted_rank_counts[1][1] == 2:
            return FULL_HOUSE
        if is_flush:
            return FLUSH
        if is_straight:
            return STRAIGHT
        if sorted_rank_counts[0][1] == 3:
            return THREE_OF_A_KIND
        if sorted_rank_counts[0][1] == 2 and sorted_rank_counts[1][1] == 2:
            return TWO_PAIR
        if sorted_rank_counts[0][1] == 2:
            return ONE_PAIR
        return HIGH_CARD

    def _get_hand_strength(self, hand: List[str], community: List[str]) -> int:
        """Compute hand strength using 2 hole cards and community cards."""
        cache_key = tuple(sorted(hand) + sorted(community))
        if cache_key in self.hand_strength_cache:
            return self.hand_strength_cache[cache_key]
        
        all_cards = [self._convert_card(c) for c in hand + community]
        best_category = 0
        for combo in itertools.combinations(all_cards, 5):
            category = self._eval_hand_category_of_5(combo)
            if category > best_category:
                best_category = category
    
        self.hand_strength_cache[cache_key] = best_category
        return best_category

    def _preflop_hand_strength(self, hand: List[str]) -> int:
        """Evaluate pre-flop hand strength."""
        card_values = sorted([RANK_TO_VALUE[c[:-1]] for c in hand], reverse=True)
        val1, val2 = card_values
        suited = hand[0][-1] == hand[1][-1]
        
        # Premium pocket pairs
        if val1 == val2:
            if val1 >= 13: return 40  # AA, KK
            if val1 >= 11: return 30  # QQ, JJ
            if val1 >= 9: return 20   # TT, 99
            return 10
        
        # High card holdings
        gap = val1 - val2
        if val1 == 14:  # Ace high
            if val2 >= 12: return 30  # AK, AQ
            if val2 >= 10 and gap <= 2: return 25
            return 5
        
        if val1 >= 13:  # King high
            if val2 >= 10 and gap < 3: return 25
            return 10
        
        if val1 == 12 and val2 == 11 and suited:  # QJs
            return 20
            
        if val1 >= 10 and val2 >= 10 and gap < 3:
            return 15
            
        return 5

    def _position_factor(self, position_index: int) -> float:
        """Calculate position-based aggression factor."""
        # Positions: BB (Worst) -> Small Blind -> Button (Best)
        # Create aggression factor based on position
        normalized_position = 1 - (position_index / (self.active_players - 1))
        aggression_factor = 0.3 + normalized_position * 0.7  # Ranges from 0.3 (early) to 1.0 (late)
        return aggression_factor

    def _stage_aggression(self, stage: str) -> float:
        """Calculate aggression by game stage."""
        multipliers = {
            'Preflop': 0.6,
            'Flop': 0.75,
            'Turn': 0.85,
            'River': 1.0
        }
        return multipliers.get(stage, 0.7)

    def _calculate_total_strength(self, hand_strength_value: float, stage_factor: float, position_factor: float) -> float:
        """Calculate total decision strength with context."""
        return hand_strength_value * stage_factor * position_factor

    def _build_strategy(self, total_strength: float, fold_edge: float, call_edge: float, raise_edge: float) -> Tuple[PokerAction, int]:
        """Determine action based on strength thresholds."""
        if total_strength < call_edge:
            return (PokerAction.FOLD, 0)
        elif call_edge <= total_strength < raise_edge:
            return (PokerAction.CALL, 0)
        else:
            if total_strength > 32:
                return (PokerAction.ALL_IN, 0)
            else:
                raise_amount = self.preflop_open_raise_amount * 0.7
                return (PokerAction.RAISE, int(raise_amount))

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, 
                 big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]) -> None:
        """Store starting cards and blind info on new hand."""
        self.hole_cards = player_hands
        self.big_blind_amount = blind_amount
        self.preflop_open_raise_amount = blind_amount * 3
        self.active_players = len(all_players)
        
        # Determine position index relative to dealer
        dealer_index = (small_blind_player_id + 1) % self.active_players
        self.player_position = (all_players.index(self.id) - dealer_index) % self.active_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        """Update stage factor and reset cache at round start."""
        self.remaining_chips = remaining_chips
        self.stage_factor = self._stage_aggression(round_state.round)
        self.hand_strength_cache = {}

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Determine action based on game state and hand strength."""
        my_bet = round_state.player_bets.get(str(self.id), 0)
        amount_to_call = round_state.current_bet - my_bet
        
        # Calculate position-based aggression factor
        position_factor = self._position_factor(self.player_position)

        if round_state.round == "Preflop":
            hand_strength_value = self._preflop_hand_strength(self.hole_cards)
        else:
            hand_strength_value = self._get_hand_strength(self.hole_cards, round_state.community_cards) * 2
        
        total_strength = self._calculate_total_strength(
            hand_strength_value, 
            self.stage_factor, 
            position_factor
        )
        
        # Strategy thresholds
        fold_edge = 7
        call_edge = 18
        raise_edge = 25
        
        # Adjust thresholds based on amount to call relative to stack
        call_threshold = min(0.25, 0.4 - (amount_to_call / self.remaining_chips))
        
        # Default to conservative action
        action, amount = (PokerAction.CHECK, 0)
        if amount_to_call > 0:
            if total_strength > call_edge:
                action, amount = (PokerAction.CALL, 0)
                
                # Upgrade to raise with strong hands
                if total_strength > 30 and round_state.max_raise > self.big_blind_amount * 2:
                    raise_amount = min(self.big_blind_amount * 3, round_state.max_raise)
                    action, amount = (PokerAction.RAISE, raise_amount)
            else:
                action = PokerAction.FOLD
        else:
            # Position-based actions when not facing a bet
            if total_strength > call_edge * position_factor:
                action, amount = self._build_strategy(total_strength, fold_edge, call_edge, raise_edge)
        
        # Switch to all-in for critical situations
        if amount > 0 and my_bet + amount_to_call + amount >= self.remaining_chips:
            action, amount = (PokerAction.ALL_IN, 0)
        
        return (action, amount)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        """Update chip count after round."""
        self.remaining_chips = remaining_chips

    def on_end_game(self, round_state: RoundStateClient, player_score: float, 
                   all_scores: dict, active_players_hands: dict) -> None:
        """Log game results for future analysis."""
        pass