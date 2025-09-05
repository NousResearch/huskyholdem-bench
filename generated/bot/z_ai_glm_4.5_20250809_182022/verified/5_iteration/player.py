from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hand_groups = {
            'AA': 1, 'KK': 1, 'QQ': 1, 'JJ': 1, 'AKs': 1, 
            'AKo': 2, 'AQs': 2, 'AJs': 2, 'KQs': 2, 'TT': 3,
            'AQo': 3, 'ATs': 3, 'KJs': 3, 'QJs': 3, 'JTs': 3,
            '99': 4, 'A9s': 4, 'KTs': 4, 'QTs': 4, 'J9s': 4,
            'T9s': 4, '88': 5, 'A8s': 5, 'K9s': 5, 'Q9s': 5,
            'J8s': 5, 'T8s': 5, '98s': 5, '77': 6, 'A7s': 6,
            'K8s': 6, 'QTs': 6, 'JTs': 6, 'T7s': 6, '87s': 6,
            '66': 7, 'A6s': 7, 'K7s': 7, 'Q8s': 7, 'J9s': 7,
            'T9s': 7, '86s': 7, '76s': 7, '55': 8, 'A5s': 8,
            'K6s': 8, 'Q7s': 8, 'J7s': 8, 'T8s': 8, '96s': 8,
            '85s': 8, '75s': 8, '44': 9, 'A4s': 9, 'K5s': 9,
            'Q6s': 9, 'J6s': 9, 'T7s': 9, '97s': 9, '86s': 9,
            '65s': 9, '33': 10, 'A3s': 10, 'K4s': 10, 'Q5s': 10,
            'J5s': 10, 'T6s': 10, '95s': 10, '87s': 10, '76s': 10,
            '22': 11, 'A2s': 11, 'K3s': 11, 'Q4s': 11, 'J4s': 11,
            'T5s': 11, '96s': 11, '85s': 11, '75s': 11, '54s': 11
        }
        self.our_hand = None
        self.starting_chips = 10000
        self.blind_level = 0
        self.position_factor = 0
        self.rand = __import__('random')
        
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_level = blind_amount
        self.our_hand = player_hands
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        if round_state.current_player:
            player_count = len(round_state.current_player)
            try:
                our_index = round_state.current_player.index(self.id)
                self.position_factor = our_index / player_count
            except ValueError:
                self.position_factor = 0.5
                
    def get_hand_key(self, hand: List[str]) -> str:
        rank_order = 'AKQJT98765432'
        c1, c2 = hand[0], hand[1]
        r1, r2 = c1[0], c2[0]
        s1, s2 = c1[1], c2[1]
        
        if r1 == r2:
            return r1 + r2
            
        higher_r = r1 if rank_order.index(r1) < rank_order.index(r2) else r2
        lower_r = r2 if higher_r == r1 else r1
        suited = 's' if s1 == s2 else 'o'
        return higher_r + lower_r + suited
        
    def evaluate_hand_strength(self, hand: List[str], community_cards: List[str]) -> float:
        all_cards = hand + community_cards
        rank_vals = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
        ranks = [card[0] for card in all_cards]
        suits = [card[1] for card in all_cards]
        
        rank_count = {}
        suit_count = {}
        for rank in ranks:
            rank_count[rank] = rank_count.get(rank, 0) + 1
        for suit in suits:
            suit_count[suit] = suit_count.get(suit, 0) + 1
            
        counts = sorted(rank_count.values(), reverse=True)
        flush = max(suit_count.values()) >= 5
        straight = self.is_straight(ranks, rank_vals)
        
        if counts[0] == 4:
            return 0.95
        elif counts[0] == 3 and counts[1] == 2:
            return 0.9
        elif flush and straight:
            return 0.99
        elif flush:
            return 0.8
        elif straight:
            return 0.7
        elif counts[0] == 3:
            return 0.6
        elif counts[0] == 2 and counts[1] == 2:
            return 0.4
        elif counts[0] == 2:
            return 0.2
        else:
            max_rank = max(rank_vals[r] for r in ranks)
            return min(max_rank / 14.0, 0.15)
            
    def is_straight(self, ranks: List[str], rank_vals: dict) -> bool:
        unique_ranks = list(set(ranks))
        if len(unique_ranks) < 5:
            return False
        sorted_vals = sorted([rank_vals[r] for r in unique_ranks], reverse=True)
        
        for i in range(len(sorted_vals) - 4):
            if sorted_vals[i] - sorted_vals[i+4] == 4:
                return True
                
        if 14 in sorted_vals and 2 in sorted_vals and 3 in sorted_vals and 4 in sorted_vals and 5 in sorted_vals:
            return True
        return False
        
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        if not round_state.current_player:
            return PokerAction.FOLD, 0
            
        current_bet = round_state.current_bet
        our_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = current_bet - our_bet
        pot = round_state.pot
        min_raise = round_state.min_raise
        max_raise = round_state.max_raise
        
        hand_key = self.get_hand_key(self.our_hand)
        hand_group = self.hand_groups.get(hand_key, 12)
        
        adjusted_group = hand_group - self.position_factor * 2
        
        if round_state.round == 'Preflop':
            if our_bet >= current_bet:  
                if adjusted_group <= 4 and self.rand.random() < 0.7:
                    if min_raise <= remaining_chips:
                        raise_amt = min(min_raise * 2, max_raise)
                        return PokerAction.RAISE, raise_amt
                return PokerAction.CHECK, 0
            else:
                if to_call == 0:
                    return PokerAction.CHECK, 0
                    
                pot_odds = to_call / (pot + to_call + 1e-6)
                
                if adjusted_group <= 2:
                    if min_raise <= remaining_chips and to_call < self.blind_level * 4:
                        raise_amt = min(min_raise * 2, max_raise, remaining_chips)
                        return PokerAction.RAISE, raise_amt
                    else:
                        return PokerAction.CALL, 0
                elif adjusted_group <= 5:
                    if pot_odds < 0.2 and to_call < self.blind_level * 3:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0
                else:
                    if pot_odds < 0.1 and to_call <= self.blind_level:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0
        else:
            hand_strength = self.evaluate_hand_strength(self.our_hand, round_state.community_cards)
            
            if our_bet >= current_bet:
                if hand_strength > 0.75:
                    bet_size = min(pot // 2, max_raise, remaining_chips)
                    if bet_size >= min_raise:
                        return PokerAction.RAISE, bet_size
                elif hand_strength > 0.6 and self.rand.random() < 0.5:
                    bet_size = min(pot // 3, max_raise, remaining_chips)
                    if bet_size >= min_raise:
                        return PokerAction.RAISE, bet_size
                return PokerAction.CHECK, 0
            else:
                pot_odds = to_call / (pot + to_call + 1e-6)
                
                if hand_strength > 0.85:
                    if min_raise <= remaining_chips:
                        raise_amt = min(min_raise * 2, max_raise, remaining_chips)
                        return PokerAction.RAISE, raise_amt
                    return PokerAction.CALL, 0
                elif hand_strength > 0.65:
                    if pot_odds < 0.3:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0
                elif hand_strength > 0.45 and pot_odds < 0.15:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
                    
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass
        
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass