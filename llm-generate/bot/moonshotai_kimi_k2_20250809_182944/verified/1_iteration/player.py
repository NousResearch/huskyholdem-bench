from typing import List, Tuple, Dict, Any
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random
import math

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 10000
        self.current_hand = []
        self.community_cards = []
        self.opponent_stats = {}
        self.position = None
        self.blind_amount = 0
        self.tight_aggressive = True
        self.stage_adjustments = {
            'Preflop': 1.0,
            'Flop': 1.2,
            'Turn': 1.3,
            'River': 1.4
        }
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.current_hand = player_hands
        for player_id in all_players:
            if player_id != self.id:
                self.opponent_stats[player_id] = {
                    'hands_played': 0,
                    'hands_raised': 0,
                    'hands_aggressive': 0,
                    'total_contribution': 0
                }
    
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.current_round = round_state
        self.community_cards = round_state.community_cards
        
    def _calculate_hand_strength(self):
        """Calculate relative hand strength"""
        if not self.community_cards:
            return self._preflop_strength()
        else:
            return self._postflop_strength()
    
    def _preflop_strength(self):
        """Evaluate preflop hand strength"""
        card1, card2 = self.current_hand
        rank1, suit1 = card1[0], card1[1]
        rank2, suit2 = card2[0], card2[1]
        
        ranks = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        rank_val1 = ranks[rank1]
        rank_val2 = ranks[rank2]
        
        is_pocket_pair = rank_val1 == rank_val2
        is_suited = suit1 == suit2
        high_card = max(rank_val1, rank_val2)
        low_card = min(rank_val1, rank_val2)
        
        # Premium hands
        if (high_card >= 10 and is_pocket_pair) or (high_card == 14 and low_card >= 10):
            return 0.9
        elif (high_card >= 10 and is_suited) or (is_pocket_pair and high_card >= 7):
            return 0.75
        elif (high_card >= 11) or (high_card >= 9 and is_suited):
            return 0.6
        elif high_card >= 9 or (high_card >= 8 and is_suited):
            return 0.45
        else:
            return 0.3
    
    def _postflop_strength(self):
        """Evaluate postflop hand strength based on board texture"""
        from itertools import combinations
        
        all_cards = self.current_hand + self.community_cards
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                   '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        def evaluate_7_cards(cards):
            ranks = [rank_map[card[0]] for card in cards]
            suits = [card[1] for card in cards]
            
            # Check flush
            from collections import Counter
            suit_counts = Counter(suits)
            flush_suit = None
            for suit, count in suit_counts.items():
                if count >= 5:
                    flush_suit = suit
                    break
            
            all_seven = list(zip(ranks, suits))
            
            # Check straight flush/straight/flush
            if flush_suit:
                flush_cards = [r for r, s in all_seven if s == flush_suit]
                flush_cards = list(set(flush_cards))
                flush_cards.sort(reverse=True)
                
                for i in range(len(flush_cards) - 4):
                    if len(flush_cards) >= 5 and max(flush_cards[i:i+5]) - min(flush_cards[i:i+5]) == 4:
                        return 8 + max(flush_cards[i:i+5]) / 14.0
                
                # Check for A-2-3-4-5 straight
                if 14 in flush_cards and sum(1 for r in range(2, 6) if r in flush_cards) == 4:
                    return 8 + 5 / 14.0
            
            # Check quads
            rank_counts = Counter(ranks)
            quads = [r for r, count in rank_counts.items() if count >= 4]
            if quads:
                kicker = max([r for r in ranks if r != quads[0]], default=2)
                return 7 + quads[0]/14.0 + kicker/(14*14)
            
            # Check full house
            trips = sorted([r for r, count in rank_counts.items() if count == 3], reverse=True)
            pairs = sorted([r for r, count in rank_counts.items() if count == 2], reverse=True)
            if trips and pairs:
                return 6 + trips[0]/14.0 + pairs[0]/(14*14)
            elif len(trips) >= 2:
                return 6 + trips[0]/14.0 + trips[1]/(14*14)
            
            # Check flush
            if flush_suit:
                flush_ranks = flush_cards[:5]
                value = 5
                for i, r in enumerate(flush_ranks):
                    value += r / (14 ** (i + 1))
                return value
            
            # Check straight
            unique_ranks = sorted(set(ranks), reverse=True)
            straight_high = 0
            for i in range(len(unique_ranks) - 4):
                if unique_ranks[i] - unique_ranks[i+4] == 4:
                    straight_high = unique_ranks[i]
                    break
            
            if not straight_high and 14 in unique_ranks:
                if all(r in unique_ranks for r in range(2, 6)):
                    straight_high = 5
            
            if straight_high:
                return 4 + straight_high/14.0
            
            # Check trips
            if trips:
                kickers = sorted([r for r in ranks if r != trips[0]], reverse=True)[:2]
                value = 3 + trips[0]/14.0
                for i, k in enumerate(kickers):
                    value += k / (14 ** (i + 2))
                return value
            
            # Check two pair
            if len(pairs) >= 2:
                high_pair, low_pair = pairs[0], pairs[1]
                kicker = max([r for r in ranks if r not in {high_pair, low_pair}])
                return 2 + high_pair/14.0 + low_pair/(14*14) + kicker/(14*14*14)
            elif len(pairs) == 1:
                kickers = sorted([r for r in ranks if r != pairs[0]], reverse=True)[:3]
                value = 1 + pairs[0]/14.0
                for i, k in enumerate(kickers):
                    value += k / (14 ** (i + 2))
                return value
            else:
                # High card
                high_cards = sorted(ranks, reverse=True)[:5]
                value = 0
                for i, r in enumerate(high_cards):
                    value += r / (14 ** (i + 1))
                return value
        
        best_rank = 0
        for combo in combinations(all_cards, 5):
            rank = evaluate_7_cards(all_cards)
            if rank > best_rank:
                best_rank = rank
        
        # Normalize relative to possible hand strength range
        return min(max(best_rank / 9.0, 0), 1)
    
    def _calculate_pot_odds(self, round_state: RoundStateClient, remaining_chips: int):
        """Calculate pot odds to determine if calling is profitable"""
        if round_state.current_bet <= 0:
            return 1.0
            
        to_call = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        if to_call <= 0:
            return 1.0
            
        pot_odds = to_call / (round_state.pot + to_call)
        return pot_odds
    
    def _adjust_for_position(self, round_state: RoundStateClient):
        """Adjust aggression based on position"""
        player_count = len(round_state.current_player)
        if player_count <= 2:
            # Heads-up play
            return 1.3
        else:
            # Multi-way pot
            return 0.9
    
    def _opponent_tendencies(self, round_state: RoundStateClient):
        """Adjust based on opponent play history"""
        if not self.opponent_stats:
            return 1.0
            
        tightness = 1.0
        for player_id, stats in self.opponent_stats.items():
            if stats['hands_played'] > 0:
                vpip = stats['hands_played'] / max(stats['total_contribution'], 1)
                if vpip > 0.3:
                    tightness = 0.8
                else:
                    tightness = 1.2
        return tightness
    
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        hand_strength = self._calculate_hand_strength()
        pot_odds = self._calculate_pot_odds(round_state, remaining_chips)
        position_factor = self._adjust_for_position(round_state)
        opponent_factor = self._opponent_tendencies(round_state)
        
        stage_adjustment = self.stage_adjustments.get(round_state.round, 1.0)
        
        # Calculate adjusted strength
        adjusted_strength = hand_strength * stage_adjustment * position_factor * opponent_factor
        
        to_call = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        
        # Decision logic
        if adjusted_strength > 0.8:
            # Very strong hand
            if to_call <= 0:
                if remaining_chips > round_state.min_raise:
                    raise_amount = min(round_state.pot * 0.8, round_state.max_raise)
                    if raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, int(raise_amount))
                return (PokerAction.CHECK, 0)
            else:
                if adjusted_strength * remaining_chips > to_call * 1.5:
                    if remaining_chips > round_state.min_raise:
                        raise_amount = min(round_state.pot * 0.9, round_state.max_raise)
                        if raise_amount >= round_state.min_raise:
                            return (PokerAction.RAISE, int(raise_amount))
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.CALL, 0)
                    
        elif adjusted_strength > 0.6:
            # Strong hand
            if to_call <= 0:
                if remaining_chips > round_state.min_raise and random.random() < 0.7:
                    raise_amount = min(round_state.pot * 0.5, round_state.max_raise)
                    if raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, int(raise_amount))
                return (PokerAction.CHECK, 0)
            else:
                if pot_odds < adjusted_strength * 1.2:
                    if remaining_chips > round_state.min_raise and adjusted_strength > 0.7:
                        raise_amount = min(max(to_call * 2, round_state.pot * 0.6), round_state.max_raise)
                        if raise_amount >= round_state.min_raise:
                            return (PokerAction.RAISE, int(raise_amount))
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
                    
        elif adjusted_strength > 0.4:
            # Marginal hand
            if to_call <= 0:
                return (PokerAction.CHECK, 0)
            else:
                if pot_odds < adjusted_strength:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        else:
            # Weak hand
            if to_call <= 0:
                return (PokerAction.CHECK, 0)
            else:
                # Semi-bluff with very small chance
                if random.random() < 0.05 and remaining_chips > round_state.min_raise:
                    raise_amount = min(round_state.pot * 0.8, round_state.max_raise)
                    if raise_amount >= round_state.min_raise:
                        return (PokerAction.RAISE, int(raise_amount))
                return (PokerAction.FOLD, 0)
    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update opponent tracking
        for player_id, action in round_state.player_actions.items():
            if player_id == str(self.id):
                continue
            
            pid = int(player_id)
            if pid in self.opponent_stats:
                stats = self.opponent_stats[pid]
                stats['total_contribution'] += 1
                
                if 'Call' in action or 'Raise' in action or 'Check' in action:
                    stats['hands_played'] += 1
                    if 'Raise' in action or 'All_in' in action:
                        stats['hands_raised'] += 1
                        stats['hands_aggressive'] += 1
    
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Reset tracking for new game
        self.opponent_stats.clear()