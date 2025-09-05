from typing import List, Tuple, Dict
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hand_strength_preflop = {}
        self._initialize_hand_strength_preflop()
        self.player_id = None
        self.starting_chips = 0
        self.blind_amount = 0

    def _initialize_hand_strength_preflop(self):
        # This is a simplified preflop hand strength guide.
        # A real bot would use a complex equity calculator.
        # For simplicity, using a basic ranking.
        # Key: (card1_rank, card2_rank, suited_or_offsuited)
        # Ranks: 2-14 (2 to Ace)
        # Suited: 's', Offsuited: 'o'
        # Pairs: e.g., 'AA', 'KK', etc.
        # Strong: AA, KK, QQ, AKs, AQs, JJ
        # Medium: TT, AJs, KQs, ATo, KJo, QJo, 99
        # Weak: all others
        
        # Example strategy buckets:
        # 3.0: Top 2% (AA, KK)
        # 2.5: Next 3% (QQ, AKs)
        # 2.0: Next 5% (JJ, AQs, KQs, AKo)
        # 1.5: Next 10% (TT, AJs, KJs, QJs, AQo, KQo, 99)
        # 1.0: Next 15% (88, ATo, KTo, QTo, JTo, suited connectors 98s, T9s, JTs)
        # 0.5: Marginal (small pairs, weaker suited connectors, broadways)
        # 0.0: Fold
        
        # This is a very rough sketch. A proper implementation would map all 169 starting hands.
        # We'll use a qualitative approach based on common wisdom.
        
        # Rankings (higher is better)
        # Pocket Pairs
        self.hand_strength_preflop['AA'] = 3.0
        self.hand_strength_preflop['KK'] = 2.9
        self.hand_strength_preflop['QQ'] = 2.8
        self.hand_strength_preflop['JJ'] = 2.7
        self.hand_strength_preflop['TT'] = 2.6
        self.hand_strength_preflop['99'] = 2.5
        self.hand_strength_preflop['88'] = 2.4
        self.hand_strength_preflop['77'] = 2.3
        self.hand_strength_preflop['66'] = 2.2
        self.hand_strength_preflop['55'] = 2.1
        self.hand_strength_preflop['44'] = 2.0
        self.hand_strength_preflop['33'] = 1.9
        self.hand_strength_preflop['22'] = 1.8

        # Suited Connectors/Gappers & Broadways
        self.hand_strength_preflop['AKs'] = 2.9
        self.hand_strength_preflop['AQs'] = 2.8
        self.hand_strength_preflop['AJs'] = 2.7
        self.hand_strength_preflop['ATs'] = 2.6
        self.hand_strength_preflop['KQs'] = 2.7
        self.hand_strength_preflop['KJs'] = 2.6
        self.hand_strength_preflop['KTs'] = 2.5
        self.hand_strength_preflop['QJs'] = 2.6
        self.hand_strength_preflop['QTs'] = 2.5
        self.hand_strength_preflop['JTs'] = 2.5
        self.hand_strength_preflop['T9s'] = 2.4
        self.hand_strength_preflop['98s'] = 2.3
        self.hand_strength_preflop['87s'] = 2.2
        self.hand_strength_preflop['76s'] = 2.1
        self.hand_strength_preflop['65s'] = 2.0
        self.hand_strength_preflop['54s'] = 1.9
        self.hand_strength_preflop['43s'] = 1.8
        self.hand_strength_preflop['32s'] = 1.7 # Low suited connectors
        
        # Offsuit Broadways
        self.hand_strength_preflop['AKo'] = 2.6
        self.hand_strength_preflop['AQo'] = 2.5
        self.hand_strength_preflop['AJo'] = 2.4
        self.hand_strength_preflop['QKo'] = 2.4 # Adjusted from KJo to QKo
        self.hand_strength_preflop['KQo'] = 2.4
        self.hand_strength_preflop['KJo'] = 2.3
        self.hand_strength_preflop['QJo'] = 2.2
        self.hand_strength_preflop['JTo'] = 2.1

        # All other hands are assumed to have a lower/folding strength for this bot
        # Any hand not explicitly listed will default to 0.0 or a low value.
        # This implicitly creates a folding range.

    def _get_hand_key(self, hand: List[str]) -> str:
        if not hand or len(hand) != 2:
            return ""

        rank1 = hand[0][0]
        suit1 = hand[0][1]
        rank2 = hand[1][0]
        suit2 = hand[1][1]

        # Convert face cards to common rank representation for comparison
        rank_map = {'T': '10', 'J': '11', 'Q': '12', 'K': '13', 'A': '14'}
        num_rank1 = int(rank_map.get(rank1, rank1))
        num_rank2 = int(rank_map.get(rank2, rank2))

        suited = 's' if suit1 == suit2 else 'o'

        if num_rank1 == num_rank2:
            return rank1 + rank2 # e.g., 'AA', 'KK'
        else:
            # Always put the higher rank first
            if num_rank1 < num_rank2:
                rank1, rank2 = rank2, rank1
            
            # Map back to char for consistency
            char_rank_map = {v: k for k, v in rank_map.items()}
            char_rank1 = char_rank_map.get(str(num_rank1), str(num_rank1))
            char_rank2 = char_rank_map.get(str(num_rank2), str(num_rank2))

            return char_rank1 + char_rank2 + suited

    def _get_preflop_strength(self, hand: List[str]) -> float:
        hand_key = self._get_hand_key(hand)
        return self.hand_strength_preflop.get(hand_key, 0.0) # Default to 0.0 for unknown hands

    def set_id(self, player_id: int) -> None:
        self.player_id = player_id
        super().set_id(player_id)

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.player_hands = player_hands # This is for current player
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players
        self.last_action = {} # Track last action for each player, not strictly necessary for this simple bot but good practice
        self.current_hand_strength = 0.0 # Will be estimated per round
        
    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.current_hand_strength = self._get_preflop_strength(self.player_hands)
        # print(f"Player {self.player_id}: Starting round {round_state.round_num}, My hand: {self.player_hands}, Strength: {self.current_hand_strength}")

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        current_bet_to_match = round_state.current_bet - round_state.player_bets.get(str(self.player_id), 0)
        
        # Ensure remaining_chips is not zero for calculations to avoid ZeroDivisionError
        if remaining_chips <= 0:
            return (PokerAction.FOLD, 0) # Already out of chips or incorrectly called to act

        # Determine betting aggressiveness based on hand strength and round
        aggressiveness_factor = self.current_hand_strength

        # Adjust aggressiveness based on round
        if round_state.round == 'Flop':
            # Need to estimate post-flop hand strength, but for simplicity,
            # this bot uses pre-flop strength + a small boost for hitting something.
            # A real bot would analyze community cards.
            aggressiveness_factor *= 1.2 # Slightly more aggressive on flop if hand was good pre-flop
        elif round_state.round == 'Turn':
            aggressiveness_factor *= 1.5 # Even more aggressive
        elif round_state.round == 'River':
            aggressiveness_factor *= 2.0 # Most aggressive on river if good hand

        # Number of active players can influence strategy
        num_active_players = len(round_state.current_player)

        # Decide action based on strength and current bet
        if current_bet_to_match == 0:  # No bet to match, can check or raise
            if aggressiveness_factor >= 2.0: # Strong hands, raise
                return self._aggressive_action(round_state, remaining_chips, current_bet_to_match)
            elif aggressiveness_factor >= 1.0: # Medium hands, check/call small raise, maybe bet for value
                 # Basic check/bet decision. Bet if pot is small relative to stack and we have a medium hand
                 # Or if no one has bet yet.
                if random.random() < 0.3 * (aggressiveness_factor / 1.0): # 30% chance to bet with medium hand
                    return self._value_bet(round_state, remaining_chips, current_bet_to_match)
                else:
                    return (PokerAction.CHECK, 0)
            else: # Weak hands, check
                return (PokerAction.CHECK, 0)
        else: # Bet to match
            # print(f"Player {self.player_id}: Current bet to match: {current_bet_to_match}")
            # If current bet is very high, consider folding
            if current_bet_to_match >= remaining_chips: # Opponent all-in or nearly all-in
                if aggressiveness_factor >= 2.5: # Only call very strong hands
                    return (PokerAction.ALL_IN, 0)
                else:
                    return (PokerAction.FOLD, 0)
            
            # Calculate pot odds for call
            # Total pot after current bets: round_state.pot + current_bet_to_match (what we are adding)
            # Risk: current_bet_to_match
            # Reward: round_state.pot + current_bet_to_match
            # If we call current_bet_to_match, the pot will be round_state.pot + current_bet_to_match
            # Odds = current_bet_to_match / (round_state.pot + current_bet_to_match)
            # This is simplified and doesn't account for future betting rounds or implied odds.

            # Simplified pot odds: how much we need to contribute vs. total pot after we contribute
            # This is incorrect to calculate pot odds and shouldn't be used directly like this from just the pot
            # A better way is:
            # amount_to_call = current_bet_to_match
            # current_pot_size = round_state.pot
            # pot_odds_ratio = amount_to_call / (current_pot_size + amount_to_call + (remaining_chips - amount_to_call))
            # or simplify it based on chips needed vs actual pot size
            # For now, we simplify: if the bet is a large fraction of our chips, be very careful.
            
            # Simple thresholding based on bet size relative to stack
            bet_fraction = current_bet_to_match / max(1, remaining_chips) # Prevent division by zero
            
            if aggressiveness_factor >= 2.5: # Premium hands
                return self._aggressive_action(round_state, remaining_chips, current_bet_to_match)
            elif aggressiveness_factor >= 1.5: # Strong hands
                if bet_fraction < 0.25: # Call if bet is less than 25% of our stack
                    return (PokerAction.CALL, 0)
                elif bet_fraction < 0.5 and num_active_players <= 2: # Maybe raise/call if heads-up and not too big
                    return self._aggressive_action(round_state, remaining_chips, current_bet_to_match)
                else:
                    return (PokerAction.FOLD, 0)
            elif aggressiveness_factor >= 0.5: # Marginal hands
                if bet_fraction < 0.1: # Call small bets
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0) # Fold to larger bets
            else: # Weakest hands
                return (PokerAction.FOLD, 0)
                
    def _aggressive_action(self, round_state: RoundStateClient, remaining_chips: int, current_bet_to_match: int) -> Tuple[PokerAction, int]:
        # Always try to raise a meaningful amount, or go all-in if justified
        min_raise_amount = round_state.min_raise
        max_raise_amount = round_state.max_raise
        
        # Calculate a raise amount. A simple strategy is to bet a percentage of the pot or a multiple of the current bet.
        pot_size = round_state.pot
        
        # If no previous bet (current_bet_to_match is 0), open raise
        if current_bet_to_match == 0:
            # Open raise to 2.5-3x Big Blind (adjusted by preflop strength) or a direct multiple of the blind
            # For simplicity, let's target 3x BB, or 0.75x pot
            raise_target_amount = max(3 * self.blind_amount, round(0.75 * pot_size))
            
            # Ensure raise is at least min_raise and within bounds
            raise_amount = max(min_raise_amount, raise_target_amount)
            
            # Cap at max_raise_amount (remaining chips)
            if raise_amount > max_raise_amount:
                return (PokerAction.ALL_IN, 0)
            else:
                return (PokerAction.RAISE, raise_amount)

        # If there's a bet to match, decide to re-raise or call/all-in
        # Re-raise to 2x the current bet, or 0.75x pot, or go all-in
        re_raise_target = current_bet_to_match + max(min_raise_amount, round(current_bet_to_match * 2))
        
        # Ensure the raise is at least min_raise (which is current_bet + min_raise_amount implicitly)
        # The amount returned for RAISE is the total amount committed from start of round.
        # So we need to calculate: current_bet + raise_amount_above_current_bet
        # A simpler way: round_state provides min_raise already as the total amount to raise to.
        
        # Option 1: Raise to a multiple of current bet (e.g., 2.5x the last bet)
        # Last bet amount is `current_bet_to_match` from antagonist perspective
        
        # The `min_raise` from `round_state` is the minimum total bet amount required to raise.
        # So, if we want to raise, the amount we provide to `RAISE` action should be `min_raise` or higher.
        
        # Consider going all-in if current bet is a significant portion of our stack or we are very strong.
        if (current_bet_to_match / max(1, remaining_chips)) > 0.4 or self.current_hand_strength >= 2.9: # High % call or very strong hand
            return (PokerAction.ALL_IN, 0)
        
        # Otherwise, make a calculated raise
        # Ideal raise amount (total chips committed FOR THE ROUND)
        desired_raise_total = current_bet_to_match + max(min_raise_amount, round_state.pot * 0.5) # Pot-sized raise
        
        # Clamp to bounds and our stack
        raise_amount = max(round_state.min_raise, desired_raise_total) # Ensure it's at least the minimum allowed raise
        
        # Ensure we don't bet more than we have
        if raise_amount >= remaining_chips:
            return (PokerAction.ALL_IN, 0)
        else:
            return (PokerAction.RAISE, raise_amount)


    def _value_bet(self, round_state: RoundStateClient, remaining_chips: int, current_bet_to_match: int) -> Tuple[PokerAction, int]:
        # Bet small for value, e.g., 1/2 pot
        if current_bet_to_match > 0: # Can't value bet if already facing a bet, need to call/raise
            return (PokerAction.CALL, 0) # Fallback to call if somehow called here with a bet

        bet_amount = round(round_state.pot * 0.5) # Half pot bet
        
        # Ensure bet is at least the big blind for readability in micro-stakes
        bet_amount = max(bet_amount, self.blind_amount)
        
        # Ensure bet is within min_raise and max_raise bounds
        bet_amount = max(round_state.min_raise, bet_amount) # This accounts for min raise including previous bet.
                                                              # For initial bet, min_raise will be current_bet + BB

        if bet_amount >= remaining_chips:
            return (PokerAction.ALL_IN, 0)
        else:
            return (PokerAction.RAISE, bet_amount)


    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # print(f"Player {self.player_id}: Round ended. Remaining chips: {remaining_chips}")
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # print(f"Player {self.player_id}: Game ended. Final score: {player_score}")
        pass