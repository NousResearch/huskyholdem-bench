import collections
import itertools
from typing import List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

#
# Hand Evaluation Logic
# These helper functions determine the strength of a poker hand.
#

_RANKS = '23456789TJQKA'
_RANK_MAP = {rank: i for i, rank in enumerate(_RANKS, 2)}

def _parse_card(card_str: str) -> Tuple[int, str]:
    """Converts a card string (e.g., 'Ah') into a numerical rank and suit tuple (e.g., (14, 'h'))."""
    try:
        rank = _RANK_MAP[card_str[0]]
        suit = card_str[1]
        return rank, suit
    except (KeyError, IndexError):
        return 0, ''

def _evaluate_5_card_hand(hand: List[Tuple[int, str]]) -> Tuple:
    """
    Evaluates a 5-card hand and returns a sortable tuple representing its strength.
    The tuple format is (hand_type, primary_rank, secondary_rank, ...kickers).
    Example: Full House, Aces over Kings -> (7, 14, 13)
    """
    ranks = sorted([card[0] for card in hand], reverse=True)
    suits = [card[1] for card in hand]
    
    is_flush = len(set(suits)) == 1
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = len(unique_ranks) == 5 and (unique_ranks[0] - unique_ranks[4] == 4)
    is_ace_low_straight = unique_ranks == [14, 5, 4, 3, 2]

    # Re-assign ranks for ace-low straight to ensure correct sorting (A=1)
    straight_ranks = ranks
    if is_ace_low_straight:
        straight_ranks = [5, 4, 3, 2, 1]

    if is_straight and is_flush:
        return (9, tuple(straight_ranks))  # Straight Flush
    if is_ace_low_straight and is_flush:
        return (9, tuple(straight_ranks))

    rank_counts = collections.Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)
    
    if counts[0] == 4:
        four_rank = [r for r, c in rank_counts.items() if c == 4][0]
        kicker = [r for r, c in rank_counts.items() if c == 1][0]
        return (8, four_rank, kicker)  # Four of a Kind

    if counts == [3, 2]:
        three_rank = [r for r, c in rank_counts.items() if c == 3][0]
        pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
        return (7, three_rank, pair_rank)  # Full House

    if is_flush:
        return (6, tuple(ranks))  # Flush

    if is_straight or is_ace_low_straight:
        return (5, tuple(straight_ranks))  # Straight
    
    if counts[0] == 3:
        three_rank = [r for r, c in rank_counts.items() if c == 3][0]
        kickers = tuple(sorted([r for r, c in rank_counts.items() if c == 1], reverse=True))
        return (4, three_rank, *kickers)  # Three of a Kind

    if counts == [2, 2, 1]:
        pair_ranks = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
        kicker = [r for r, c in rank_counts.items() if c == 1][0]
        return (3, tuple(pair_ranks), kicker) # Two Pair

    if counts[0] == 2:
        pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
        kickers = tuple(sorted([r for r, c in rank_counts.items() if c == 1], reverse=True))
        return (2, pair_rank, *kickers) # One Pair

    return (1, tuple(ranks))  # High Card

def evaluate_best_hand(hole_cards: List[str], community_cards: List[str]) -> Tuple:
    """Finds the best 5-card hand from the given hole and community cards."""
    if not hole_cards or len(hole_cards) != 2:
        return (0, (0,))
    
    all_cards_str = hole_cards + community_cards
    if len(all_cards_str) < 5:
        # Not enough cards for a full hand, can't evaluate yet
        return (0, (0,))

    all_cards = [_parse_card(c) for c in all_cards_str]
    
    best_hand_rank = (0, (0,))
    for hand_combo in itertools.combinations(all_cards, 5):
        current_rank = _evaluate_5_card_hand(list(hand_combo))
        if current_rank > best_hand_rank:
            best_hand_rank = current_rank
            
    return best_hand_rank

def score_hole_cards(hole_cards: List[str]) -> float:
    """Generates a pre-flop score for hole cards (higher is better)."""
    if not hole_cards or len(hole_cards) != 2:
        return 0.0

    card1, card2 = [_parse_card(c) for c in hole_cards]
    r1, s1 = card1
    r2, s2 = card2
    
    high_rank, low_rank = (r1, r2) if r1 > r2 else (r2, r1)
    
    score = 0
    if high_rank == 14: score = 10
    elif high_rank == 13: score = 8
    elif high_rank == 12: score = 7
    elif high_rank == 11: score = 6
    else: score = high_rank / 2.0

    if r1 == r2: # Pair
        score = max(5, score * 2)

    if s1 == s2: # Suited
        score += 2

    gap = high_rank - low_rank - 1
    if gap >= 0:
        if gap == 0 and r1 != r2: score += 1 # Connector
        elif gap == 1: score -= 1
        elif gap == 2: score -= 2
        elif gap == 3: score -= 4
        else: score -= 5
    
    return score

class SimplePlayer(Bot):
    """
    A simple but effective poker bot that plays a tight-aggressive strategy.
    It evaluates hand strength carefully and bets proportionally to its confidence.
    """
    def __init__(self):
        super().__init__()
        self.hole_cards: List[str] = []
        self.total_players: int = 0
        self.blind_amount: int = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        """Called once at the start of the game simulation."""
        self.total_players = len(all_players)
        self.blind_amount = blind_amount
        # The hole cards for the first round are provided here. For subsequent rounds,
        # we assume the game runner updates self.hole_cards before on_round_start.
        self.hole_cards = player_hands

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """
        Called at the start of a new hand.
        We assume the game runner has updated self.hole_cards with the new hand.
        """
        # Reset any per-round state here if needed in future versions.
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """Core logic for deciding the bot's action."""
        
        # --- 1. GATHER VITAL INFO ---
        my_bet = round_state.player_bets.get(str(self.id), 0)
        to_call = round_state.current_bet - my_bet
        can_check = to_call == 0

        # Number of players still in the hand (haven't folded).
        # We estimate this from the number of players who have placed bets.
        active_players = len(round_state.player_bets)
        if active_players == 0 and self.total_players > 0: # Pre-flop, before actions
            active_players = self.total_players

        # If hole cards are not available, play safely.
        if not self.hole_cards:
            return (PokerAction.CHECK, 0) if can_check else (PokerAction.FOLD, 0)

        # --- 2. PRE-FLOP STRATEGY ---
        if round_state.round == 'Preflop':
            preflop_score = score_hole_cards(self.hole_cards)
            
            # Define thresholds based on score and number of players
            aggression_factor = 1.0 - (active_players / (self.total_players + 1)) # More aggressive with fewer players
            raise_threshold = 8.5 + aggression_factor 
            call_threshold = 6.5 + aggression_factor

            # Standard raise size: 2.5x the big blind
            raise_amount = int(self.blind_amount * 2.5)

            # If someone has already raised, we need to re-evaluate
            if round_state.current_bet > self.blind_amount:
                raise_amount = int(round_state.current_bet * 3) # Re-raise 3x
                call_threshold += 1 # Be more selective when calling a raise
            
            # Ensure raise is valid
            raise_amount = max(raise_amount, round_state.min_raise)
            raise_amount = min(raise_amount, remaining_chips)

            if preflop_score >= raise_threshold:
                if raise_amount > remaining_chips:
                    return PokerAction.ALL_IN, remaining_chips
                return PokerAction.RAISE, raise_amount
            
            if preflop_score >= call_threshold and to_call < remaining_chips * 0.2: # Don't call off a huge chunk of stack
                 if to_call > 0:
                     return PokerAction.CALL, 0
                 else: # Limp in
                     return PokerAction.CALL, 0

            # Default action: fold unless we can check for free (as big blind)
            return (PokerAction.CHECK, 0) if can_check else (PokerAction.FOLD, 0)

        # --- 3. POST-FLOP STRATEGY ---
        else:
            hand_strength = evaluate_best_hand(self.hole_cards, round_state.community_cards)
            hand_type = hand_strength[0] # 1 for High Card, 9 for Straight Flush

            # Strong hand (Two Pair or better) -> Bet for value
            if hand_type >= 3:
                # Bet 50-75% of the pot
                bet_amount = int(round_state.pot * 0.66)
                
                # If facing a bet, raise instead of just calling
                if not can_check:
                    # Pot-sized raise: pot + 2*bet_to_call
                    raise_amount = round_state.pot + 2 * to_call
                    bet_amount = min(raise_amount, remaining_chips)
                
                bet_amount = max(bet_amount, round_state.min_raise) # Must be at least min_raise
                bet_amount = min(bet_amount, remaining_chips) # Cannot bet more than we have
                
                if bet_amount >= remaining_chips:
                    return PokerAction.ALL_IN, remaining_chips
                return PokerAction.RAISE, bet_amount

            # Decent hand (One Pair) -> Cautious play
            if hand_type == 2:
                # Bet if no one else has, otherwise call small bets
                if can_check:
                    bet_amount = int(round_state.pot * 0.5)
                    bet_amount = min(bet_amount, remaining_chips)
                    if bet_amount >= round_state.min_raise:
                         return PokerAction.RAISE, bet_amount
                    else:
                         return PokerAction.CHECK, 0
                else:
                    # Check pot odds: call if profitable
                    pot_odds = to_call / (round_state.pot + to_call + 1e-9)
                    # We'll call if the bet is less than 25% of the pot
                    if pot_odds < 0.25 and to_call < remaining_chips:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0
            
            # Weak hand or draw -> Check/Fold
            if can_check:
                return PokerAction.CHECK, 0
            else:
                return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the end of a hand. Can be used for opponent modeling in future."""
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """Called at the very end of the game simulation."""
        # This hook could be used for analysis or logging final results.
        pass