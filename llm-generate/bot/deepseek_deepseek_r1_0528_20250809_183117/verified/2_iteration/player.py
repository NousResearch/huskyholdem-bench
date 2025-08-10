from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import random
from itertools import combinations
from enum import Enum
from dataclasses import dataclass
import sys
import math

class PokerAction(Enum):
    FOLD = 1
    CHECK = 2
    CALL = 3
    RAISE = 4
    ALL_IN = 5

class PokerRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

@dataclass
class RoundStateClient:
    round_num: int
    round: str
    community_cards: List[str]
    pot: int
    current_player: List[int]
    current_bet: int
    min_raise: int
    max_raise: int
    player_bets: Dict[str, int]
    player_actions: Dict[str, str]
    side_pots: Optional[List[Dict[str, Any]] = None

    @classmethod
    def from_message(cls, message: Dict[str, Any]) -> 'RoundStateClient':
        return cls(
            round_num=message['round_num'],
            round=message['round'],
            community_cards=message['community_cards'],
            pot=message['pot'],
            current_player=message['current_player'],
            current_bet=message['current_bet'],
            min_raise=message['min_raise'],
            max_raise=message['max_raise'],
            player_bets=message['player_bets'],
            player_actions=message.get('player_actions', {}),
            side_pots=message.get('side_pots', [])
        )

class Bot(ABC):
    def __init__(self) -> None:
        self.id: Optional[int] = None
        self.name = "SimplePlayer"

    def set_id(self, player_id: int) -> None:
        self.id = player_id

    @abstractmethod
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]) -> None:
        pass

    @abstractmethod
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        pass

    @abstractmethod
    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        pass

    @abstractmethod
    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        pass

    @abstractmethod
    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict) -> None:
        pass

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards: List[str] = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.position = 0
        self.initial_players = 0
        self.current_round = None
        self.round_stage_names = ["Preflop", "Flop", "Turn", "River"]
        self.hand_strength = 0.0
        self.equity = 0.0
        self.active_players = 0
        self.last_aggressor = -1
        self.previous_action = None

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, 
                big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]) -> None:
        self.hole_cards = player_hands
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.initial_players = len(all_players)
        self.active_players = len(all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        self.current_round = round_state.round
        self.active_players = len([b for b in round_state.player_bets.values() if b >= 0])

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            community_cards = round_state.community_cards
            current_bet = round_state.current_bet
            player_bet = round_state.player_bets.get(str(self.id), 0)
            amount_to_call = max(0, current_bet - player_bet)
            min_raise = round_state.min_raise
            max_raise = min(round_state.max_raise, remaining_chips)

            # Determine position and opponent aggression
            aggressor = self._detect_aggressor(round_state.player_actions)

            # Calculate hand strength based on current stage
            stage = self.round_stage_names.index(round_state.round) if round_state.round in self.round_stage_names else 0
            self.hand_strength = self._calculate_hand_strength(self.hole_cards, community_cards, num_samples=100)

            # Pot odds calculation
            pot_odds = self._calculate_pot_odds(amount_to_call, round_state.pot) if amount_to_call > 0 else float('inf')
            equity = self._estimate_equity(self.hole_cards, community_cards, num_opponents=self.active_players-1, num_samples=50)

            # Position-based adjustments
            position_factor = self._get_position_factor(round_state)
            stack_size = remaining_chips / self.starting_chips
            
            # Decision making by stage
            round_map = {
                "Preflop": self._handle_preflop,
                "Flop": self._handle_flop,
                "Turn": self._handle_turn,
                "River": self._handle_river
            }
            
            action_handler = round_map.get(round_state.round, self._handle_preflop)
            action, amount = action_handler(
                round_state, amount_to_call, min_raise, max_raise, pot_odds, equity, position_factor, aggressor, stack_size
            )
            
            # Always validate and correct invalid raises
            if action == PokerAction.RAISE:
                if self._is_min_raise_invalid(min_raise, amount, max_raise, amount_to_call):
                    if min_raise > max_raise - amount_to_call:
                        action = PokerAction.ALL_IN
                        return action, 0
                    amount = min_raise
                else:
                    amount = min(max_raise, max(amount, min_raise))
                    
            return action, amount

        except Exception as e:
            # Safe fallback to fold on any exception
            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int) -> None:
        self.previous_action = PokerAction.FOLD if remaining_chips == 0 else None

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict) -> None:
        pass

    # Helper Methods --------------------------------------------------------------
    
    def _get_position_factor(self, state: RoundStateClient) -> float:
        """Return position factor (0=early, 1=late)"""
        player_index = state.current_player.index(self.id)
        return player_index / len(state.current_player)
    
    def _is_min_raise_invalid(self, min_raise: int, amount: int, max_raise: int, amount_to_call: int) -> bool:
        return min_raise > max_raise or amount < min_raise
    
    def _calculate_pot_odds(self, amount_to_call: int, pot_size: int) -> float:
        if amount_to_call <= 0:
            return float('inf')
        return (amount_to_call) / (pot_size + amount_to_call + 1e-5)
    
    def _get_hand_group(self):
        """Return Sklansky hand group (1-8)"""
        ranks = [c[0] for c in self.hole_cards]
        suits = [c[1] for c in self.hole_cards]
        is_pair = ranks[0] == ranks[1]
        is_suited = suits[0] == suits[1]
        high_rank = max(ranks, key=lambda r: '23456789TJQKA'.index(r))
        low_rank = min(ranks, key=lambda r: '23456789TJQKA'.index(r))

        # Group 1: Premium pairs and AKs
        if is_pair and high_rank in 'AKQJ':
            return 1
        if not is_pair and high_rank == 'A' and low_rank == 'K' and is_suited:
            return 1
        
        # Group 2: Strong pairs and Broadway
        if is_pair and high_rank in 'T9':
            return 2
        if not is_pair and high_rank == 'A' and low_rank in 'QJ' and is_suited:
            return 2
        
        # Group 3: Medium pairs and suited connectors
        if is_pair and high_rank in '87':
            return 3
        if not is_pair and is_suited and high_rank in 'KQ' and low_rank in 'JT':
            return 3
        
        # Group 4: Smaller pairs and suited broadways
        if is_pair and high_rank in '65432':
            return 4
        if not is_pair and is_suited and high_rank in 'ATKQJ':
            return 4
        
        # Group 5: Weak suited aces and connectors
        if not is_pair and is_suited and high_rank == 'A' and low_rank in '98765432':
            return 5
        
        return 8  # Default to fold tier

    def _calculate_hand_strength(self, hole_cards: List[str], community_cards: List[str], num_samples: int = 100) -> float:
        """Estimate hand strength using Monte Carlo simulation"""
        if len(community_cards) == 0:
            return self._get_hand_group() / 8.0
            
        if len(community_cards) == 5:  # River scenario
            return self._simulate_exact_hand_strength(hole_cards, community_cards)

        return self._estimate_equity(hole_cards, community_cards, num_opponents=self.active_players-1, num_samples=num_samples)

    def _simulate_exact_hand_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        """Evaluate exact hand ranking on river"""
        RANK_VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        ranks = [RANK_VALUES[c[0]] for c in hole_cards + community_cards]

        if max(ranks) > 14:
            return 0.0
            
        try:
            hand_score = self._evaluate_hand_rank(hole_cards + community_cards)
            # Normalize to 0-1 range empirically
            if hand_score > 8000: return 0.99
            if hand_score > 6000: return 0.85
            if hand_score > 4000: return 0.65
            if hand_score > 2000: return 0.45
            if hand_score > 1000: return 0.25
            return 0.1
        except:
            return 0.0

    def _estimate_equity(self, hole_cards: List[str], community: List[str], num_opponents: int, num_samples: int) -> float:
        """Monte Carlo equity estimation"""
        if num_opponents < 1 or len(community) >= 5:
            return self._simulate_exact_hand_strength(hole_cards, community)

        # Generate remaining deck
        all_cards = [f"{r}{s}" for r in '23456789TJQKA' for s in 'shdc']
        dead_cards = hole_cards + community
        deck = [c for c in all_cards if c not in dead_cards]

        if len(deck) < num_opponents * 2:
            return 0.0

        wins = 0
        for _ in range(num_samples):
            # Shuffle and deal
            random.shuffle(deck[:len(deck)])  # Shuffle in limited range
            
            # Deal opponent holes and remaining cards
            opp_holes = [deck[i:i+2] for i in range(0, num_opponents * 2, 2)]
            remaining_deck = deck[num_opponents * 2:]
            
            # Deal remaining community cards
            remaining_community = 5 - len(community)
            board = community + remaining_deck[:remaining_community]
            remaining_deck = remaining_deck[remaining_community:]
            
            # Evaluate our hand
            our_hand = self._evaluate_raw_hand(hole_cards + board)
            opp_hands = [self._evaluate_raw_hand(oh + board) for oh in opp_holes]
            
            if min(opp_hands) > our_hand:  # We win only if we beat all opponents
                wins += 1
        
        return wins / num_samples

    def _evaluate_hand_rank(self, cards: List[str]) -> int:
        """Evaluate 5-7 cards hand to numerical rank (higher=better)"""
        if len(cards) < 5:
            return 0

        best_rank = self._evaluate_raw_hand(cards)
        return best_rank

    def _evaluate_raw_hand(self, cards: List[str]) -> int:
        """Core hand evaluation for 5+ cards"""
        RANK_VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        if len(cards) < 5:
            return 0

        value_cards = []
        suits = []
        for card in cards:
            rank_char = card[0]
            suit_char = card[1]
            value_cards.append(RANK_VALUES[rank_char])
            suits.append(suit_char)

        # Check for flush
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
            
        flush_suit = None
        for suit, count in suit_counts.items():
            if count >= 5:
                flush_suit = suit
                break

        # Build flush cards
        flush_cards = [value_cards[i] for i in range(len(cards)) if suits[i] == flush_suit] if flush_suit else []
        flush_cards = sorted(flush_cards, reverse=True)[:5] if flush_cards else []
        
        # Straight detection
        all_straights = []
        for combo in combinations(value_cards, min(5, len(value_cards))):
            combo_sorted = sorted(combo, reverse=True)
            if combo_sorted[0] == combo_sorted[4] + 4 and len(set(combo_sorted)) == 5:
                all_straights.append(combo_sorted[0])
            # Ace-low straight
            if 14 in combo_sorted:
                ace_low = [x for x in combo_sorted if x != 14] + [1]
                ace_low_sorted = sorted(ace_low, reverse=True)
                if len(ace_low_sorted) >= 5 and ace_low_sorted[0] == 5 and ace_low_sorted[4] == 1:
                    all_straights.append(5)

        # Card frequency analysis
        rank_counts = {}
        for rank in value_cards:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
        by_count = {}
        for rank, count in rank_counts.items():
            by_count.setdefault(count, []).append(rank)
            
        for key in by_count:
            by_count[key].sort(reverse=True)

        # Prioritize hand categories
        if flush_suit and all_straights and max(all_straights) == 14 and len(flush_cards) >= 5:
            return 10**8  # Royal flush
        
        if flush_suit and all_straights:
            return 10**7 + max(all_straights)  # Straight flush
        
        if 4 in by_count:
            quads = by_count[4][0]
            kickers = sorted(value_cards, reverse=True)
            kickers = [k for k in kickers if k != quads][:1]
            return 10**6 + quads * 100 + kickers[0]  # Four of a kind
        
        if 3 in by_count and 2 in by_count:
            trips = by_count[3][0]
            pairs = by_count[2][0]
            return 10**5 + trips * 100 + pairs  # Full house
        
        if flush_suit:
            return 10**4 + flush_cards[0] * 100 + flush_cards[1]  # Flush
        
        if all_straights:
            return 10**3 + max(all_straights)  # Straight
            
        if 3 in by_count:
            trips = by_count[3][0]
            kickers = sorted(value_cards, reverse=True)
            kickers = [k for k in kickers if k != trips][:2]
            return 10**2 + trips * 100 + kickers[0]*10 + kickers[1]
            
        if 2 in by_count and len(by_count[2]) >= 2:
            pair_high = by_count[2][0]
            pair_low = by_count[2][1]
            kickers = sorted(value_cards, reverse=True)
            kickers = [k for k in kickers if k not in [pair_r for pair_r in by_count[2]][:2]][:1]
            return 10 + pair_high * 100 + pair_low * 10 + kickers[0]
            
        if 2 in by_count:
            pair = by_count[2][0]
            kickers = sorted(value_cards, reverse=True)
            kickers = [k for k in kickers if k != pair][:3]
            return 1 + pair * 1000 + kickers[0]*100 + kickers[1]*10 + kickers[2]
        
        # High card
        high_values = sorted(value_cards, reverse=True)[:5]
        score = 0
        for i, val in enumerate(high_values):
            score += val * (10**(4-i))
        return score

    def _detect_aggressor(self, actions: Dict[str, str]) -> int:
        """Detect if there was recent aggression (-1=none, 90=last aggressor)"""
        for player, action in actions.items():
            if player == str(self.id):
                continue
            if action in {"RAISE", "ALL_IN"}:
                return 90
        return -1

    # Stage Handlers --------------------------------------------------------------
    
    def _handle_preflop(self, state: RoundStateClient, to_call: int, min_raise: int, max_raise: int, 
                       pot_odds: float, equity: float, position: float, aggressor: int, stack: float) -> Tuple[PokerAction, int]:
        hand_group = self._get_hand_group()
        
        # Implementation of preflop aggression based on position and hand strength
        if to_call == 0:  # No bet facing us
            if hand_group == 1:
                raise_amount = min(max_raise, max(min_raise, self.blind_amount * 5))
                return PokerAction.RAISE, raise_amount
            elif hand_group <= 3 and position > 0.5:
                return PokerAction.RAISE, min(min_raise, max_raise)
            elif hand_group <= 4 and position > 0.7:
                return PokerAction.CHECK, 0
            else:
                return PokerAction.FOLD, 0
        else:  # Facing a bet
            aggression_factor = 1
            if aggressor > 80 and hand_group <= 3:
                # Re-raise aggressive opponent with strong hands
                raise_amt = min(max_raise, max(min_raise, min_raise * 2))
                return PokerAction.RAISE, raise_amt
            if hand_group == 1:
                return PokerAction.RAISE, min(max_raise, min_raise * 3)
            if hand_group <= 2 and pot_odds < 0.3:
                return PokerAction.CALL, 0
            if hand_group <= 3 and pot_odds < 0.2:
                return PokerAction.CALL, 0
                
            # Fold weak hands with bad pot odds
            return PokerAction.FOLD, 0

    def _handle_flop(self, state: RoundStateClient, to_call: int, min_raise: int, max_raise: int, 
                   pot_odds: float, equity: float, position: float, aggressor: int, stack: float) -> Tuple[PokerAction, int]:
        # Premium hands - maximize value
        if self.hand_strength > 0.85:
            if aggressor > 0:
                return PokerAction.RAISE, min(max_raise, min_raise * 2)
            else:
                return PokerAction.RAISE, min_raise
                
        # Medium hands - controlled betting
        if self.hand_strength > 0.6:
            if to_call == 0:
                return PokerAction.RAISE, min_raise
            if pot_odds < 0.15 or equity > 0.65:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0
            
        # Drawing hands - pot odds based decisions
        if self.hand_strength > 0.3 and equity > pot_odds and pot_odds < 0.3:
            return PokerAction.CALL, 0
            
        return PokerAction.FOLD, 0  # Weak hands fold

    def _handle_turn(self, state: RoundStateClient, to_call: int, min_raise: int, max_raise: int, 
                   pot_odds: float, equity: float, position: float, aggressor: int, stack: float) -> Tuple[PokerAction, int]:
        if self.hand_strength > 0.8:
            return PokerAction.RAISE, min_raise * 2 if aggressor > 0 else min_raise
        if self.hand_strength > 0.6:
            if aggressor > 0 and stack > 0.5:
                return PokerAction.CALL, 0
            return PokerAction.CALL, 0 if to_call == 0 else PokerAction.CALL
        if equity > pot_odds and equity > 0.3 and pot_odds < 0.35:
            return PokerAction.CALL, 0
        return PokerAction.FOLD, 0

    def _handle_river(self, state: RoundStateClient, to_call: int, min_raise: int, max_raise: int, 
                    pot_odds: float, equity: float, position: float, aggressor: int, stack: float) -> Tuple[PokerAction, int]:
        exact_strength = self._simulate_exact_hand_strength(self.hole_cards, state.community_cards)
        
        if exact_strength > 0.8:
            return PokerAction.RAISE, min_raise * 2
        if exact_strength > 0.5:
            if to_call == 0:
                return PokerAction.CHECK, 0
            if pot_odds < 0.2:
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0
        return PokerAction.FOLD, 0