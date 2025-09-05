from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.card_rank = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        self.initial_chips = 10000
        self.players_info = {}
        self.position = 0
        self.my_hand = []
        self.blind_amount = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.initial_chips = starting_chips
        self.my_hand = [player_hands[0] if player_hands[0][0] != ' ' else player_hands[1]]
        
        for i, pid in enumerate(all_players):
            if pid == self.id:
                self.position = i
                break
        
        for idx, pid in enumerate(all_players):
            self.players_info[pid] = {
                'position': idx,
                'chips': starting_chips,
                'is_bb': pid == big_blind_player_id,
                'is_sb': pid == small_blind_player_id
            }
        
        self.blind_amount = blind_amount

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        hand_strength = self.evaluate_hand_strength(round_state)
        pot_odds = self.calculate_pot_odds(round_state)
        
        bb = self.blind_amount
        current_bet = round_state.current_bet
        min_raise = round_state.min_raise
        max_raise = round_state.max_raise
        
        if current_bet == 0:
            if hand_strength > 0.7:
                raise_amount = min(max(bb * 3, 100), max_raise)
                return PokerAction.RAISE, raise_amount
            elif hand_strength > 0.4:
                return PokerAction.CHECK, 0
            else:
                return PokerAction.CHECK, 0
        else:
            to_call = current_bet - (round_state.player_bets.get(str(self.id), 0))
            
            if to_call <= max_raise - to_call:
                if hand_strength > 0.8:
                    if remaining_chips > to_call * 3:
                        raise_amount = min(max(to_call * 3, min_raise), max_raise)
                        return PokerAction.RAISE, raise_amount
                    else:
                        return PokerAction.ALL_IN, 0
                elif hand_strength > 0.6:
                    return PokerAction.CALL, 0
                elif hand_strength * pot_odds > 1.3:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
            else:
                if hand_strength > 0.85:
                    if remaining_chips > to_call:
                        return PokerAction.ALL_IN, 0
                    else:
                        return PokerAction.CALL, 0
                elif hand_strength * pot_odds > 1.8:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass

    def evaluate_hand_strength(self, round_state: RoundStateClient) -> float:
        hole_cards = self.my_hand
        if len(hole_cards) != 2:
            return 0.0
            
        card1, card2 = hole_cards[0], hole_cards[1]
        rank1 = self.card_rank[card1[0]]
        rank2 = self.card_rank[card2[0]]
        is_suited = card1[1] == card2[1]
        
        max_rank = max(rank1, rank2)
        min_rank = min(rank1, rank2)
        
        strength = 0.0
        
        if rank1 == rank2:
            strength = 0.8 - (13 - max_rank) * 0.05
        elif is_suited and (max_rank - min_rank <= 4):
            strength = 0.7 - (12 - max(max_rank, min_rank)) * 0.04
        elif not is_suited and (max_rank - min_rank == 1):
            strength = 0.6 - (12 - max(max_rank, min_rank)) * 0.04
        elif max_rank >= 10:
            strength = max_rank / 20.0
        elif min_rank >= 8:
            strength = min_rank / 25.0
        else:
            strength = max_rank / 30.0
            
        if len(round_state.community_cards) > 0:
            if len(round_state.community_cards) <= 3:
                strength *= 1.1
            elif len(round_state.community_cards) <= 4:
                strength *= 1.15
            else:
                strength *= 1.2
                made_hand = self.evaluate_made_hand(hole_cards, round_state.community_cards)
                strength = max(strength, made_hand)
                
        return min(strength, 1.0)

    def evaluate_made_hand(self, hole: List[str], board: List[str]) -> float:
        if not hole or not board:
            return 0.0
            
        all_cards = hole + board
        if len(all_cards) < 5:
            return 0.0
            
        # Simple high card evaluation
        ranks = [self.card_rank[c[0]] for c in all_cards]
        max_rank = max(ranks)
        base = max_rank / 14.0
        
        # Check pairs
        rank_counts = {}
        for r in ranks:
            rank_counts[r] = rank_counts.get(r, 0) + 1
        
        pairs = []
        for k, v in rank_counts.items():
            if v >= 2:
                pairs.append(k)
                
        if len(pairs) >= 1:
            base = max(base, 0.3 + max(pairs) / 20.0)
            
        if len(pairs) >= 2:
            base = max(base, 0.5 + max(pairs) / 15.0)
            
        for v in rank_counts.values():
            if v >= 3:
                base = max(base, 0.7)
            elif v >= 4:
                base = 1.0
                
        return base

    def calculate_pot_odds(self, round_state: RoundStateClient) -> float:
        pot = round_state.pot
        to_call = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        
        if to_call <= 0:
            return float('inf')
        if pot <= 0:
            return 0.0
            
        return pot / float(to_call + 1e-6)