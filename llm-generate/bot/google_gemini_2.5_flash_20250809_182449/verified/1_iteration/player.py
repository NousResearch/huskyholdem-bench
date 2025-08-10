from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
from enum import Enum

class PokerRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 0
        self.player_id = None
        self.blind_amount = 0
        self.all_players = []
        self.num_players = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.hole_cards = player_hands
        self.blind_amount = blind_amount
        self.all_players = all_players
        self.num_players = len(all_players)

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.hole_cards = round_state.player_hands.get(str(self.id), []) if hasattr(round_state, 'player_hands') else []


    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        current_bet_to_match = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        
        # Determine hand strength (very basic for this example)
        # This is a placeholder; a real bot would use a complex hand evaluator
        hand_strength = self._evaluate_hand_strength(self.hole_cards, round_state.community_cards)

        # Basic strategy based on hand strength and round
        if round_state.round == 'Preflop':
            if hand_strength >= 0.8: # Very strong hands (AA, KK, AKs, etc.)
                return self._ aggressive_action(round_state, remaining_chips, current_bet_to_match)
            elif hand_strength >= 0.5: # Medium strong hands (suited connectors, pocket pairs, etc.)
                if current_bet_to_match == 0:
                    return PokerAction.CHECK, 0
                elif current_bet_to_match <= self.blind_amount * 2: # Call small bets
                    return PokerAction.CALL, 0
                elif current_bet_to_match <= self.blind_amount * 4 and remaining_chips > current_bet_to_match:
                    return PokerAction.CALL, 0
                else: # Fold against large pre-flop raises
                    return PokerAction.FOLD, 0
            else: # Weak hands
                if current_bet_to_match == 0:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0
        else: # Post-flop rounds (Flop, Turn, River)
            if hand_strength >= 0.9: # Very strong hands (made straights, flushes, trips, etc.)
                return self._ aggressive_action(round_state, remaining_chips, current_bet_to_match)
            elif hand_strength >= 0.7: # Strong hands (top pair, two pair)
                if current_bet_to_match == 0:
                    return PokerAction.CHECK, 0
                else: # Call or small raise
                    if remaining_chips > current_bet_to_match:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.ALL_IN, 0
            elif hand_strength >= 0.4: # Medium hands (middle pair, draws)
                if current_bet_to_match == 0:
                    return PokerAction.CHECK, 0
                elif current_bet_to_match < remaining_chips / 4: # Call if bet is small relative to stack
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
            else: # Weak hands
                if current_bet_to_match == 0:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0

    def _aggressive_action(self, round_state: RoundStateClient, remaining_chips: int, current_bet_to_match: int) -> Tuple[PokerAction, int]:
        min_raise_amount = max(round_state.min_raise, current_bet_to_match + self.blind_amount * 2)

        if min_raise_amount <= remaining_chips:
            action_amount = min(min_raise_amount, remaining_chips)
            if action_amount == remaining_chips:
                return PokerAction.ALL_IN, 0
            return PokerAction.RAISE, action_amount
        elif current_bet_to_match <= remaining_chips:
            return PokerAction.CALL, 0
        else:
            return PokerAction.ALL_IN, 0

    def _evaluate_hand_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        """
        A very simplified hand strength evaluator.
        This needs to be replaced with a proper poker hand evaluator for competition.
        For now, it's just a placeholder, relying on hole cards.
        """
        if not hole_cards or len(hole_cards) < 2:
            return 0.0

        card_ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        suits = ['c', 'd', 'h', 's']

        # Extract ranks and suits from hole cards
        rank1 = hole_cards[0][0]
        suit1 = hole_cards[0][1]
        rank2 = hole_cards[1][0]
        suit2 = hole_cards[1][1]

        # Convert to numerical ranks for comparison
        num_rank1 = card_ranks.index(rank1)
        num_rank2 = card_ranks.index(rank2)

        # Pair check
        if rank1 == rank2:
            if rank1 in ['A', 'K']: return 0.9 # AA, KK
            if rank1 in ['Q', 'J', 'T']: return 0.8 # QQ, JJ, TT
            return 0.7 # Other pairs
        
        # Suited connectors/Broadway
        if suit1 == suit2:
            # Suited Broadway (AKs, AQs, KQs, etc.)
            if (num_rank1 >= card_ranks.index('T') and num_rank2 >= card_ranks.index('T')) or \
               (num_rank1 == card_ranks.index('A') and num_rank2 >= card_ranks.index('T')) or \
               (num_rank2 == card_ranks.index('A') and num_rank1 >= card_ranks.index('T')):
                return 0.8
            # Suited connectors (JTs, T9s, etc.)
            if abs(num_rank1 - num_rank2) <= 4: # Gap of at most 3 for suited connectors
                return 0.6
        
        # Unsuited Broadway
        if (num_rank1 >= card_ranks.index('T') and num_rank2 >= card_ranks.index('T')) or \
           (num_rank1 == card_ranks.index('A') and num_rank2 >= card_ranks.index('T')) or \
           (num_rank2 == card_ranks.index('A') and num_rank1 >= card_ranks.index('T')):
            return 0.7

        # High cards
        if num_rank1 >= card_ranks.index('Q') or num_rank2 >= card_ranks.index('Q'):
            return 0.5

        # Other hands
        return 0.3

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass