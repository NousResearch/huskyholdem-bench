from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.my_hand = []
        self.starting_chips = 10000
        self.remaining_chips = 10000
        self.player_id = None
        self.all_players = []
        self.big_blind_player_id = None
        self.small_blind_player_id = None
        self.blind_amount = 0
        self.round_count = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.my_hand = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players
        self.round_count = 0

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.remaining_chips = remaining_chips
        self.round_count += 1

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            my_current_bet = round_state.player_bets.get(str(self.id), 0)
            to_call = round_state.current_bet - my_current_bet

            # Hand strength estimation
            hand_strength = self._evaluate_hand_strength(self.my_hand, round_state.community_cards)

            # Positional awareness - are we last to act?
            is_last_to_act = str(self.id) == str(round_state.current_player[-1]) if round_state.current_player else False

            # Preflop logic
            if round_state.round == 'Preflop':
                return self._preflop_strategy(round_state, hand_strength, to_call, remaining_chips, is_last_to_act)

            # Postflop logic
            else:
                return self._postflop_strategy(round_state, hand_strength, to_call, remaining_chips, is_last_to_act)

        except Exception as e:
            return (PokerAction.FOLD, 0)

    def _evaluate_hand_strength(self, hand: List[str], community_cards: List[str]) -> float:
        # Simplified hand strength evaluator - can be improved with more sophisticated logic
        # Returns value between 0.0 (worst) and 1.0 (best)
        
        # High card base strength
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        if not hand:
            return 0.0
            
        try:
            # Extract ranks and suits
            hand_ranks = [rank_values[card[0]] for card in hand]
            hand_suits = [card[1] for card in hand]
            
            all_cards = hand + community_cards
            all_ranks = [rank_values[card[0]] for card in all_cards]
            all_suits = [card[1] for card in all_cards]
            
            # Check for pair, two pair, three of a kind, etc.
            rank_counts = {}
            for rank in all_ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
                
            sorted_counts = sorted(rank_counts.values(), reverse=True)
            
            # Evaluate basic hand type
            if len(community_cards) == 0:  # Preflop
                # Pocket pairs
                if hand_ranks[0] == hand_ranks[1]:
                    if hand_ranks[0] >= 10:  # Big pocket pair
                        return 0.8 + (hand_ranks[0] - 10) * 0.04
                    else:  # Small pocket pair
                        return 0.5 + (hand_ranks[0] - 2) * 0.03
                # High cards
                elif max(hand_ranks) >= 12 or min(hand_ranks) >= 10:  # Ace or King, or both high
                    return 0.6 + (max(hand_ranks) - 10) * 0.05
                # Connected or suited
                elif abs(hand_ranks[0] - hand_ranks[1]) <= 4 or hand_suits[0] == hand_suits[1]:
                    return 0.4 + (max(hand_ranks) - 2) * 0.02
                else:
                    return 0.2 + (max(hand_ranks) - 2) * 0.01
                    
            else:  # Postflop
                # Full house or better
                if sorted_counts[0] >= 3 and len(sorted_counts) > 1 and sorted_counts[1] >= 2:
                    return 0.95
                # Three of a kind
                elif sorted_counts[0] >= 3:
                    return 0.85
                # Two pair
                elif sorted_counts[0] >= 2 and len(sorted_counts) > 1 and sorted_counts[1] >= 2:
                    return 0.7
                # One pair
                elif sorted_counts[0] >= 2:
                    return 0.5
                # High card
                else:
                    high_card_strength = max(all_ranks) / 14.0
                    return 0.1 + high_card_strength * 0.3
                    
        except:
            return 0.0

    def _preflop_strategy(self, round_state: RoundStateClient, hand_strength: float, to_call: int, remaining_chips: int, is_last_to_act: bool) -> Tuple[PokerAction, int]:
        # Positional adjustment
        position_factor = 1.0
        if str(self.id) == str(self.small_blind_player_id):
            position_factor = 0.8
        elif str(self.id) == str(self.big_blind_player_id):
            position_factor = 0.9
            
        adjusted_strength = hand_strength * position_factor
        
        # Blind defense
        if str(self.id) == str(self.big_blind_player_id) and to_call <= self.blind_amount:
            if adjusted_strength > 0.4:
                return (PokerAction.CALL, 0)
            elif round_state.min_raise <= remaining_chips and adjusted_strength > 0.6:
                raise_amount = min(round_state.min_raise * 2, remaining_chips)
                return (PokerAction.RAISE, raise_amount)
            else:
                return (PokerAction.CALL, 0)
                
        if str(self.id) == str(self.small_blind_player_id) and to_call <= self.blind_amount/2:
            if adjusted_strength > 0.5:
                return (PokerAction.CALL, 0)
            else:
                return (PokerAction.FOLD, 0)

        # Opening ranges
        if to_call == 0:  # We can check or open
            if adjusted_strength > 0.7:  # Premium hands
                raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.03)), remaining_chips)
                return (PokerAction.RAISE, raise_amount)
            elif adjusted_strength > 0.5:  # Good hands
                raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.02)), remaining_chips)
                return (PokerAction.RAISE, raise_amount)
            elif adjusted_strength > 0.3 and is_last_to_act:  # Speculative hands in position
                raise_amount = min(max(round_state.min_raise, int(remaining_chips * 0.015)), remaining_chips)
                return (PokerAction.RAISE, raise_amount)
            else:
                return (PokerAction.CHECK, 0)
        else:  #Facing a raise
            if adjusted_strength > 0.8:  # Premium hands
                if to_call <= remaining_chips * 0.1:
                    raise_amount = min(round_state.min_raise * 3, remaining_chips)
                    return (PokerAction.RAISE, raise_amount)
                elif to_call <= remaining_chips * 0.2:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            elif adjusted_strength > 0.6:  # Strong hands
                if to_call <= remaining_chips * 0.08:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            elif adjusted_strength > 0.4:  # Marginal hands
                if to_call <= remaining_chips * 0.03:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                return (PokerAction.FOLD, 0)

    def _postflop_strategy(self, round_state: RoundStateClient, hand_strength: float, to_call: int, remaining_chips: int, is_last_to_act: bool) -> Tuple[PokerAction, int]:
        pot_odds = to_call / (round_state.pot + to_call + 1e-8)  # Add small epsilon to prevent division by zero
        
        # Bluff catching and value betting
        if hand_strength > 0.8:  # Very strong hand
            if to_call == 0:
                bet_amount = min(max(round_state.min_raise, int(round_state.pot * 0.75)), remaining_chips)
                return (PokerAction.RAISE, bet_amount)
            else:
                if to_call <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        elif hand_strength > 0.6:  # Strong hand
            if to_call == 0:
                bet_amount = min(max(round_state.min_raise, int(round_state.pot * 0.5)), remaining_chips)
                return (PokerAction.RAISE, bet_amount)
            else:
                if pot_odds <= 0.3 and to_call <= remaining_chips * 0.15:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        elif hand_strength > 0.4:  # Moderate hand
            if to_call == 0:
                # Check or small bet for protection
                if random.random() < 0.3:  # Sometimes bet for value
                    bet_amount = min(max(round_state.min_raise, int(round_state.pot * 0.3)), remaining_chips)
                    return (PokerAction.RAISE, bet_amount)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                if pot_odds <= 0.2 and to_call <= remaining_chips * 0.1:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)
        else:  # Weak hand
            if to_call == 0:
                # Occasionally bluff
                if is_last_to_act and random.random() < 0.15:
                    bet_amount = min(max(round_state.min_raise, int(round_state.pot * 0.5)), remaining_chips)
                    return (PokerAction.RAISE, bet_amount)
                else:
                    return (PokerAction.CHECK, 0)
            else:
                # Fold weak hands to bets
                return (PokerAction.FOLD, 0)

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        self.remaining_chips = remaining_chips

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass