from typing import List, Tuple, Dict, Any
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from itertools import combinations
from collections import Counter
import math

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.blind_amount = 0
        self.starting_chips = 0
        self.preflop_thresholds = {
            'no_raise': {'fold': 0.4, 'call': 0.7, 'raise': 1.0},
            'raise': {'fold': 0.6, 'call': 0.9, 'raise': 1.2}
        }
        self.position_adjustment = True
        
    def set_id(self, player_id: int) -> None:
        self.id = player_id
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]) -> None:
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        pass
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        my_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = round_state.current_bet - my_bet
        
        if round_state.round == 'Preflop':
            return self._preflop_action(round_state, remaining_chips)
        else:
            return self._postflop_action(round_state, remaining_chips)
    
    def _preflop_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        hole_cards = self._get_hole_cards(round_state)
        hand_strength = self._preflop_hand_strength(hole cards)
        
        # Determine if there's been a raise
        raised = round_state.current_bet > self.blind_amount
        
        # Get thresholds based on raise situation
        if raised:
            thresholds = self.preflop_thresholds['raise']
        else:
            thresholds = self.preflop_thresholds['no_raise']
            
        # Adjust for position
        if self.position_adjustment:
            position_strength = self._get_position_strength(round_state)
            hand_strength += position_strength * 0.1
        
        my_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = round_state.current_bet - my_bet
        
        if hand_strength < thresholds['fold']:
            return (PokerAction.FOLD, 0)
        elif hand_strength < thresholds['call']:
            if to_call == 0:
                return (PokerAction.CHECK, 0)
            else:
                return (PokerAction.CALL, to_call)
        else:
            if to_call == 0:
                action_type = PokerAction.RAISE
            else:
                action_type = PokerAction.RAISE if hand_strength >= thresholds['raise'] else PokerAction.CALL
                
            if action_type == PokerAction.CALL:
                return (PokerAction.CALL, to_call if to_call > 0 else 0)
            else:
                # Calculate raise amount (min of 2.5x pot or half our stack)
                pot_raise = int(round_state.pot * 2.5 / len(round_state.current_player))
                stack_raise = int(remaining_chips * 0.5)
                raise_amount = max(round_state.min_raise, min(pot_raise, stack_raise, round_state.max_raise))
                return (PokerAction.RAISE, raise_amount)
    
    def _postflop_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        hole_cards = self._get_hole_cards(round_state)
        all_cards = hole_cards + round_state.community_cards
        
        if len(all_cards) < 5:
            # Edge case处理
            if round_state.current_bet == 0:
                return (PokerAction.CHECK, 0)
            else:
                return (PokerAction.FOLD, 0)
                
        hand_rank, tie_breaker = self._best_hand(all_cards)
        hand_strength = self._hand_rank_to_strength(hand_rank)
        
        # Pot odds calculation
        my_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = round_state.current_bet - my_bet
        pot_odds = to_call / (round_state.pot + to_call + 1e-9)
        
        # Adjust hand strength based on board texture
        board_danger = self._assess_board_danger(round_state.community_cards)
        adjusted_strength = hand_strength * (1 - board_danger * 0.15)
        
        if adjusted_strength < pot_odds:
            if to_call == 0:
                return (PokerAction.CHECK, 0)
            else:
                return (PokerAction.FOLD, 0)
        else:
            if hand_strength > 0.85:  # Very strong hand
                if to_call == 0:
                    action = PokerAction.RAISE
                elif adjusted_strength > pot_odds * 1.5:
                    action = PokerAction.RAISE
                else:
                    action = PokerAction.CALL
                    
                if action == PokerAction.RAISE:
                    # Aggressive raise (pot-sized)
                    raise_amount = min(round_state.pot, round_state.max_raise)
                    raise_amount = max(raise_amount, round_state.min_raise)
                    return (PokerAction.RAISE, raise_amount)
                else:
                    return (PokerAction.CALL, to_call if to_call > 0 else 0)
            else:
                if to_call == 0:
                    return (PokerAction.CHECK, 0)
                else:
                    return (PokerAction.CALL, to_call)
    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        pass
        
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict) -> None:
        pass
    
    def _get_hole_cards(self, round_state: RoundStateClient) -> List[str]:
        # This is a placeholder. In real implementation, 
        # we would need to track hole cards through the game
        # For now, return empty list
        return []
    
    def _preflop_hand_strength(self, hole_cards: List[str]) -> float:
        if len(hole_cards) < 2:
            return 0.0
            
        rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, 
                      '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        
        card1 = hole_cards[0]
        card2 = hole_cards[1]
        
        r1 = rank_order[card1[0]]
        r2 = rank_order[card2[0]]
        
        high = max(r1, r2)
        low = min(r1, r2)
        
        is_pair = (r1 == r2)
        is_suited = (card1[1] == card2[1])
        
        base = (high + low) / 28.0  # 28 = 14+14 (max possible sum)
        bonus = 0.3 * base if is_pair else 0.15 * base if is_suited else 0
        strength = base + bonus
        
        return min(1.0, strength)
    
    def _get_position_strength(self, round_state: RoundStateClient) -> float:
        num_players = len(round_state.current_player)
        if num_players <= 1:
            return 0.0
            
        try:
            my_index = round_state.current_player.index(self.id)
            position_strength = my_index / (num_players - 1)
        except ValueError:
            position_strength = 0.0
            
        return position_strength
    
    def _hand_rank_to_strength(self, hand_rank: int) -> float:
        # Map hand rank to strength value [0-1]
        strength_map = {
            0: 0.1,   # High card
            1: 0.3,    # One pair
            2: 0.5,    # Two pair
            3: 0.65,   # Three of a kind
            4: 0.75,   # Straight
            5: 0.8,    # Flush
            6: 0.9,    # Full house
            7: 0.95,   # Four of a kind
            8: 1.0     # Straight flush (royal flush included)
        }
        return strength_map.get(hand_rank, 0.1)
    
    def _assess_board_danger(self, community_cards: List[str]) -> float:
        if len(community_cards) < 3:
            return 0.0
            
        # Calculate board danger level (0-1)
        suits = [card[1] for card in community_cards]
        ranks = [card[0] for card in community_cards]
        
        # Flush danger
        suit_counts = Counter(suits)
        max_suit_count = max(suit_counts.values())
        flush_danger = min(max_suit_count - 2, 3) / 3.0  # Normalize 3-5 to 0-1
        
        # Straight danger
        rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, 
                      '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        num_ranks = len(set(ranks))
        straight_danger = max(0, 5 - num_ranks) / 4.0  # More consecutive ranks = more danger
        
        # Pair danger
        rank_counts = Counter(ranks)
        pair_danger = min(max(rank_counts.values()) - 1, 2) / 2.0  # Normalize pairs/trips to 0-1
        
        return max(flush_danger, straight_danger, pair_danger)
    
    def _best_hand(self, cards: List[str]) -> Tuple[int, List[int]]:
        if len(cards) < 5:
            return (0, [])  # High card
            
        best_rank = -1
        best_tie_breaker = []
        
        for combo in combinations(cards, 5):
            rank, tie_breaker = self._evaluate_hand(list(combo))
            if rank > best_rank or (rank == best_rank and tie_breaker > best_tie_breaker):
                best_rank = rank
                best_tie_breaker = tie_breaker
                
        return (best_rank, best_tie_breaker)
    
    def _evaluate_hand(self, hand: List[str]) -> Tuple[int, List[int]]:
        rank_order = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, 
                      '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
        
        suits = [card[1] for card in hand]
        ranks = sorted([rank_order[card[0]] for card in hand])
        
        is_flush = len(set(suits)) == 1
        is_straight = self._is_straight(ranks)
        
        rank_counts = Counter(ranks)
        count_vals = sorted(rank_counts.values(), reverse=True)
        count_groups = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        
        if is_straight and is_flush:
            return (8, [max(ranks)])  # Straight flush
        elif count_vals[0] == 4:
            return (7, [count_groups[0][0], count_groups[1][0]])  # Four of a kind
        elif count_vals[0] == 3 and count_vals[1] == 2:
            return (6, [count_groups[0][0], count_groups[1][0]])  # Full house
        elif is_flush:
            return (5, sorted(ranks, reverse=True))  # Flush
        elif is_straight:
            return (4, [max(ranks)])  # Straight
        elif count_vals[0] == 3:
            return (3, [count_groups[0][0]] + sorted([r for r in ranks if r != count_groups[0][0]], reverse=True))
        elif count_vals[0] == 2 and count_vals[1] == 2:
            pair_ranks = [g[0] for g in count_groups[:2]]
            kicker = [g[0] for g in count_groups if g[1] == 1][0]
            return (2, sorted(pair_ranks, reverse=True) + [kicker])
        elif count_vals[0] == 2:
            pair_rank = count_groups[0][0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return (1, [pair_rank] + kickers)
        else:
            return (0, sorted(ranks, reverse=True))
    
    def _is_straight(self, ranks: List[int]) -> bool:
        if ranks == [2,3,4,5,14]:  # Ace-low straight
            return True
        for i in range(1, len(ranks)):
            if ranks[i] != ranks[i-1] + 1:
                return False
        return True