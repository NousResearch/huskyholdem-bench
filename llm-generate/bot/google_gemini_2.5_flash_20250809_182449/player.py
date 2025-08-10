import random
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
        self.starting_chips = 0
        self.player_hands = []
        self.blind_amount = 0
        self.big_blind_player_id = -1
        self.small_blind_player_id = -1
        self.all_players = []
        self.id = -1 # My player ID
        self.hand_strength_preflop = {}
        self._initialize_hand_strength()

    def _initialize_hand_strength(self):
        # Assign arbitrary strength values for pre-flop hands. This is a very basic model.
        # Strong pairs
        pairs = ['AA', 'KK', 'QQ', 'JJ', 'TT']
        # Suited connectors/high cards
        suited_connectors = ['AKs', 'AQs', 'AJs', 'ATs', 'KQs', 'KJs', 'QTs']
        # Off-suit high cards
        offsuit_high = ['AKo', 'AQo', 'AJo', 'KQo']

        for hand in pairs:
            self.hand_strength_preflop[hand] = 0.9 + random.uniform(-0.05, 0.05)
        for hand in suited_connectors:
            self.hand_strength_preflop[hand] = 0.7 + random.uniform(-0.05, 0.05)
        for hand in offsuit_high:
            self.hand_strength_preflop[hand] = 0.6 + random.uniform(-0.05, 0.05)

        # General approach for other hands: random value, weak.
        # This needs to be more sophisticated with actual pre-flop hand rankings.
        # For simplicity, we just generate random low values for unspecified hands
        # based on card ranks and whether they are suited/connected.
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        for i in range(len(ranks)):
            for j in range(i, len(ranks)):
                r1 = ranks[i]
                r2 = ranks[j]
                if r1 == r2: # Pair
                    if r1 + r2 not in self.hand_strength_preflop:
                        self.hand_strength_preflop[r1 + r2] = 0.5 + random.uniform(-0.05, 0.05)
                else: # Non-pair
                    suited_hand = r1 + r2 + 's'
                    offsuit_hand = r1 + r2 + 'o'
                    if suited_hand not in self.hand_strength_preflop:
                        self.hand_strength_preflop[suited_hand] = 0.4 + random.uniform(-0.05, 0.05)
                    if offsuit_hand not in self.hand_strength_preflop:
                        self.hand_strength_preflop[offsuit_hand] = 0.3 + random.uniform(-0.05, 0.05)

    def _get_hand_key(self, cards: List[str]) -> str:
        if not cards or len(cards) != 2:
            return "UNKNOWN"
        c1_rank = cards[0][0]
        c1_suit = cards[0][1]
        c2_rank = cards[1][0]
        c2_suit = cards[1][1]

        # Ensure consistent order for pairs and non-pairs (e.g., AK not KA)
        ranks_order = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        if ranks_order[c1_rank] < ranks_order[c2_rank]:
            c1_rank, c2_rank = c2_rank, c1_rank

        if c1_rank == c2_rank:
            return c1_rank + c2_rank
        elif c1_suit == c2_suit:
            return c1_rank + c2_rank + 's'
        else:
            return c1_rank + c2_rank + 'o'

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.player_hands = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players
        self.id = self.all_players[0] # Assuming my ID is the first one in all_players for now, needs to be set externally or by the system caller. This is not a reliable way to set self.id

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # Reset any round-specific state
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        my_hand_key = self._get_hand_key(self.player_hands)
        hand_strength = self.hand_strength_preflop.get(my_hand_key, 0.2) # Default to a weak hand if not specified

        current_bet_to_match = round_state.current_bet - round_state.player_bets.get(str(self.id), 0)
        
        # Determine if I am big blind or small blind and what the initial bet is
        is_big_blind = (self.id == self.big_blind_player_id)
        is_small_blind = (self.id == self.small_blind_player_id)
        
        # Simple strategy based on hand strength and betting round
        # Pre-flop strategy
        if round_state.round == 'Preflop':
            # Aggressive hands: AA, KK, QQ, AKs, AQs
            if hand_strength >= 0.8:
                if current_bet_to_match == 0: # Can check
                    return PokerAction.RAISE, min(remaining_chips, self.blind_amount * 3)
                elif current_bet_to_match < remaining_chips * 0.2: # Small bet
                    return PokerAction.RAISE, min(remaining_chips, current_bet_to_match * 2 + self.blind_amount) # Aggressive raise
                elif current_bet_to_match >= remaining_chips * 0.2 and current_bet_to_match < remaining_chips:
                    return PokerAction.CALL, 0
                else: # Bet is too high to call, but we have strong hand, so all-in
                    return PokerAction.ALL_IN, 0
            # Medium hands: JJ, TT, AJs, KQs, AKo, AQo, suited connectors
            elif 0.5 <= hand_strength < 0.8:
                if current_bet_to_match == 0:
                    return PokerAction.RAISE, min(remaining_chips, self.blind_amount * 2)
                elif current_bet_to_match <= self.blind_amount * 2: # Call if not too expensive
                    return PokerAction.CALL, 0
                else: # Bet too high for medium hand
                    return PokerAction.FOLD, 0
            # Weak hands: anything else
            else:
                if current_bet_to_match == 0 and not is_big_blind and not is_small_blind: # Just check if possible and no blinds
                    return PokerAction.CHECK, 0
                elif current_bet_to_match == 0 and is_big_blind and round_state.player_bets.get(str(self.id), 0) == self.blind_amount * 2:
                    # If I'm BB and no one raised my blind, I can check.
                    return PokerAction.CHECK, 0
                elif current_bet_to_match <= self.blind_amount: # Call only if minimal cost (small blind or limped pot)
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0
        
        # Post-flop strategy (Flop, Turn, River) - very basic, just uses general aggressiveness
        # This part of the bot does not use community cards effectively nor calculate real equity
        # A more advanced bot would re-evaluate hand strength here.
        
        # Be more aggressive if pot is small (trying to steal) or large (committed)
        pot_size = round_state.pot if round_state.pot > 0 else 1 # Avoid division by zero
        aggressiveness_factor = min(1.0, remaining_chips / pot_size) # Adjust based on stack-to-pot ratio
        
        # Randomness to make it less predictable but within strategic boundaries
        r = random.random()

        if hand_strength >= 0.7: # Strong Hand (e.g., two pair, trips, straight, flush in simple terms)
            if current_bet_to_match == 0:
                # Bet roughly 50-70% of the pot
                bet_amount = int(0.5 * round_state.pot + round_state.pot * 0.2 * r)
                return PokerAction.RAISE, min(remaining_chips, max(round_state.min_raise, bet_amount))
            elif current_bet_to_match < remaining_chips * 0.3 * aggressiveness_factor:
                # Re-raise or call, lean towards raise
                if r < 0.7: # 70% chance to raise further
                    raise_amount = min(remaining_chips, max(round_state.min_raise * 2, current_bet_to_match * 2 + self.blind_amount))
                    return PokerAction.RAISE, raise_amount
                else:
                    return PokerAction.CALL, 0
            else:
                # Bet is too high or we're pushed, consider all-in
                if r < 0.5: # 50% chance to push all-in
                     return PokerAction.ALL_IN, 0
                else:
                     return PokerAction.FOLD, 0 # Sometimes fold strong to avoid tilting
        elif 0.4 <= hand_strength < 0.7: # Medium Hand (e.g., top pair, good kicker)
            if current_bet_to_match == 0:
                # Bet roughly 30-50% of the pot
                bet_amount = int(0.3 * round_state.pot + round_state.pot * 0.2 * r)
                return PokerAction.RAISE, min(remaining_chips, max(round_state.min_raise, bet_amount))
            elif current_bet_to_match < remaining_chips * 0.15 * aggressiveness_factor:
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        else: # Weak Hand (e.g., high card, weak pair)
            if current_bet_to_match == 0:
                return PokerAction.CHECK, 0
            elif current_bet_to_match < remaining_chips * 0.05 * aggressiveness_factor:
                # Call only if very cheap
                return PokerAction.CALL, 0
            else:
                return PokerAction.FOLD, 0
        
        # Fallback for safety (shouldn't be reached with proper logic)
        return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Good place to log/analyze round results
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Game finished, final cleanup or logging
        pass