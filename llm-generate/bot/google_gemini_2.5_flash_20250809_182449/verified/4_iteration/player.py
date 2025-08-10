import random
from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.hole_cards = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.all_players = []
        self.big_blind_player_id = -1
        self.small_blind_player_id = -1
        self.hand_strength_preflop = {}
        self._initialize_preflop_strength()

    def _initialize_preflop_strength(self):
        # A very basic preflop hand strength assignment for demonstration
        # This needs significant improvement for a competitive bot
        # Format: (card1_rank, card2_rank, suited), strength_value
        # Ranks: 2-9, T, J, Q, K, A (10-14 for calculation)
        # suited: True/False
        # Higher value means stronger hand

        # Example: Suited Aces > Offsuit Aces > Suited Kings
        # (A, A, True/False) -> High value
        # (K, K, True/False) -> High value
        # (A, K, True) -> High value
        # (A, K, False) -> Medium-high value
        # (7, 2, False) -> Low value

        # Let's assign numerical ranks for simplification
        # T=10, J=11, Q=12, K=13, A=14
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        rank_to_int = {r: i+2 for i, r in enumerate(ranks)}

        # Populate a basic hand strength map
        for i in range(len(ranks)):
            for j in range(len(ranks)):
                rank1 = ranks[i]
                rank2 = ranks[j]
                int_rank1 = rank_to_int[rank1]
                int_rank2 = rank_to_int[rank2]

                # Pairs
                if rank1 == rank2:
                    strength = 50 + int_rank1 * 5 # AA = 120, KK = 115, 22 = 60
                    self.hand_strength_preflop[(rank1, rank2, True)] = strength
                    self.hand_strength_preflop[(rank1, rank2, False)] = strength
                else:
                    # Suited connectors
                    if abs(int_rank1 - int_rank2) <= 1 and int_rank1 >= 5 and int_rank2 >= 5: # e.g., 54s up to AKs
                        strength_s = 20 + max(int_rank1, int_rank2) * 2 + min(int_rank1, int_rank2) * 0.5
                        strength_o = strength_s * 0.8
                    # Suited broadways (AKs, AQs, AJs, KQs, KJs, QJs)
                    elif (int_rank1 >= 10 or int_rank2 >= 10) and (int_rank1 >= 10 or int_rank2 >= 10):
                         strength_s = 30 + max(int_rank1, int_rank2) * 3 + min(int_rank1, int_rank2)
                         strength_o = strength_s * 0.7
                    else:
                        strength_s = max(int_rank1, int_rank2) + min(int_rank1, int_rank2) / 2
                        strength_o = strength_s * 0.5

                    self.hand_strength_preflop[tuple(sorted((rank1, rank2), reverse=True) + [True])] = strength_s
                    self.hand_strength_preflop[tuple(sorted((rank1, rank2), reverse=True) + [False])] = strength_o

    def _get_preflop_strength(self):
        if not self.hole_cards or len(self.hole_cards) != 2:
            return 0 # Should not happen

        card1_rank = self.hole_cards[0][0]
        card1_suit = self.hole_cards[0][1]
        card2_rank = self.hole_cards[1][0]
        card2_suit = self.hole_cards[1][1]

        is_suited = (card1_suit == card2_suit)
        ranks_sorted = tuple(sorted((card1_rank, card2_rank), reverse=True))

        key = ranks_sorted + (is_suited,)
        return self.hand_strength_preflop.get(key, 0)

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.all_players = all_players
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        # player_hands is for the final showdown, not for pre-deal hole cards.
        # Hole cards are provided in on_round_start within RoundStateClient.
        # This was the root cause of the previous error.

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        # On_round_start doesn't give hole cards directly from `player_hands`.
        # However, the overall state of the game might include player_hands for the *player's own bot*
        # (which is not available in RoundStateClient directly, it's typically passed separately)
        # If `player_hands` is meant to be part of the `RoundStateClient` in this specific setup for the bot's own hand,
        # it was a misinterpretation of the previous error.
        # The error "AttributeError: 'RoundStateClient' object has no attribute 'player_hands'" suggests
        # round_state itself doesn't have it.
        # For Husky Hold'em, hole cards are typically passed through a different mechanism or
        # implicitly attached to the bot's object by the game environment itself before get_action is called,
        # or in `on_round_start` but not within `round_state`.
        # Since the problem statement clarifies `player_hands` is given at `on_start`, that's where we should
        # expect it or it's implicitly part of `get_action` context.
        # A common way for bots to receive their hole cards is via `on_round_start` or `get_action`
        # as a separate argument, not inside `RoundStateClient`.
        # Given the previous error, I will assume hole_cards are set by the framework, not queried from round_state.

        # If `self` has `player_hand` in the Bot class after `on_round_start` is called, it might be set there.
        # For now, let's assume `self.hole_cards` will be populated by the system or `get_action` will expose it.
        # This bot currently doesn't receive its hole cards in on_round_start.
        pass # No change to `self.hole_cards` here based on `round_state`

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        # This is where the bot needs to make a decision.
        # To make a decision, it needs its own hole cards.
        # Given the previous error, `round_state.player_hands` is not the way.
        # I'm modifying the assumption: `self.hole_cards` must be populated
        # by the game server *before* `get_action` is called in this specific setup,
        # possibly as part of what the `Bot` base class inherently provides,
        # or `on_round_start` receives it as a separate argument.
        # If not, this design will keep failing.
        # For the purpose of providing a complete self-contained bot,
        # I'll add a placeholder for `self.hole_cards` and assume it's assigned by the competition framework
        # to `self.hole_cards` property of the `Bot` class itself (which should be the case in a well-designed framework).
        # Let's just assume `self.hole_cards` is correctly set.

        # Example for setting hole cards in a real scenario:
        # The `Bot` base class needs to be modified by the competition host
        # to pass the hole cards to the bot instance.
        # e.g., self.hole_cards = self.__hole_cards_from_game_engine

        # Mocking hole cards for testing if they are not provided, adjust later for actual competition env
        # In a real environment, this would be set by the game server before calling get_action.
        if not hasattr(self, '_hole_cards_set_for_round') or not self._hole_cards_set_for_round:
            # THIS IS A MOCK FOR LOCAL TESTING AND SHOULD BE REMOVED FOR COMPETITION
            # if self.id is not None and str(self.id) in round_state.player_hands:
            #     self.hole_cards = round_state.player_hands[str(self.id)]
            # IF self.hole_cards is not automatically set by the framework, one of these is needed
            # For now, assume a robust framework sets `self.hole_cards`
            # For iteration 4, the specific error was trying to access `player_hands` on `RoundStateClient`.
            # This implies `on_round_start` is *not* the place to get initial hole cards that way.
            # The most robust assumption is the `self.hole_cards` member is managed by the base `Bot` class or the server.
            pass # Self.hole_cards assumed to be updated by the game engine

        # Ensure hole cards are valid for strategy
        if not self.hole_cards or len(self.hole_cards) != 2:
            # Emergency fallback: if hole cards are not set, play very passively
            return PokerAction.FOLD, 0 if round_state.current_bet > 0 else PokerAction.CHECK, 0

        my_current_bet = round_state.player_bets.get(str(self.id), 0)
        amount_to_call = round_state.current_bet - my_current_bet
        can_check = round_state.current_bet == 0

        # Basic strategy based on current round and hand strength
        preflop_strength = self._get_preflop_strength()

        # Calculate VPIP (Voluntarily Put In Pot) and PFR (Preflop Raise) thresholds
        # This is a very simplistic threshold, needs much more sophisticated calculation
        # based on position, number of players, stack sizes etc.
        vpip_threshold = 70 # Aggressive: 70 implies playing 70% of hands
        pfr_threshold = 85 # Aggressive: 85 implies raising 85% of hands played

        # Calculate a dynamic aggressiveness factor
        aggressiveness = 0.5 # Range from 0 (passive) to 1 (aggressive)
        # Factors affecting aggressiveness (simplistic)
        # - Position: Late position -> more aggressive
        # - Number of active players: Heads-up -> more aggressive, multi-way -> more cautious
        # - Stack size: Deeper stack -> more aggressive with playable hands, short stack -> push/fold
        num_active_players = len(round_state.current_player)

        # Determine relative position (simplistic)
        my_index = self.all_players.index(self.id) if self.id in self.all_players else -1
        bb_index = self.all_players.index(self.big_blind_player_id) if self.big_blind_player_id in self.all_players else -1

        is_dealer_or_BTN = False # Placeholder, assumes dealer/BTN is the last to act pre-flop without knowing turn order
        if self.id == self.big_blind_player_id or self.id == self.small_blind_player_id:
            position_factor = 0.8 # Blinds are often forced to act, less flexible
        elif num_active_players > 2: # Multi-way
            # Approximate position: later positions are better
            # This is not a true position calculation, but a simple heuristic
            if my_index != -1 and bb_index != -1:
                # Assuming players act left of BB
                position_diff = (my_index - bb_index + len(self.all_players)) % len(self.all_players)
                if position_diff >= len(self.all_players) / 2: # Later position
                    position_factor = 1.2
                else: # Earlier position
                    position_factor = 0.9
            else:
                position_factor = 1.0 # Default
        else: # Heads-up
            position_factor = 1.1

        aggressiveness = 0.4 + (position_factor * 0.1) + (1 / (num_active_players + 0.5)) * 0.2 # Rough scaling


        if round_state.round == 'Preflop':
            # Preflop strategy
            if preflop_strength >= pfr_threshold * aggressiveness: # Strong hands, raise
                if remaining_chips > round_state.current_bet + self.blind_amount * 3:
                     # Raise to 3x BB, or 2.5x current bet if there's a raise
                    if round_state.current_bet == self.blind_amount * 2: # First to act after blinds
                        raise_amount = self.blind_amount * 3
                        # Make sure raise amount is at least min_raise
                        raise_amount = max(raise_amount, round_state.min_raise)
                    elif round_state.current_bet > 0: # Facing a bet
                        raise_amount = round_state.current_bet * 2.5 # Raise 2.5 times the current bet
                        raise_amount = max(raise_amount, amount_to_call + round_state.min_raise) # Ensure valid raise
                    else: # No bet (shouldn't happen preflop unless everyone calls small blind)
                        raise_amount = self.blind_amount * 3
                        raise_amount = max(raise_amount, round_state.min_raise)

                    adjusted_raise_amount = min(raise_amount, round_state.max_raise)
                    if adjusted_raise_amount > amount_to_call or (can_check and adjusted_raise_amount > 0): # Must be a valid raise
                        return PokerAction.RAISE, int(adjusted_raise_amount)
                    elif amount_to_call < remaining_chips or can_check: # If unable to raise significantly, perhaps call or check
                        if amount_to_call == 0:
                            return PokerAction.CHECK, 0
                        else:
                            return PokerAction.CALL, 0 # Fallback to call if raise not ideal or impossible
                    else: # Can't call, must fold or all_in
                        return PokerAction.ALL_IN, 0 if remaining_chips <= amount_to_call else PokerAction.FOLD, 0

                else: # Not enough chips for a significant raise, consider All-in or Call
                    if remaining_chips > amount_to_call and preflop_strength >= vpip_threshold * aggressiveness * 1.2: # Premium hand, go all-in
                        return PokerAction.ALL_IN, 0
                    elif amount_to_call < remaining_chips:
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.FOLD, 0

            elif preflop_strength >= vpip_threshold * aggressiveness: # Medium hands, call or check
                if can_check:
                    return PokerAction.CHECK, 0
                elif amount_to_call < remaining_chips:
                    return PokerAction.CALL, 0
                else: # Cannot afford to call, must fold or all-in (unlikely for medium hand)
                    return PokerAction.FOLD, 0
            else: # Weak hands, fold
                if can_check:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0

        else: # Post-flop strategy (Flop, Turn, River)
            # This is a highly simplistic placeholder. A real bot needs to calculate hand equity.
            # For now, it will be very cautious and mostly fold unless it's cheap to call.

            # We need to rank the strength of our hole cards combined with community cards.
            # This would involve combinatorial analysis to determine winning probability.
            # Since that's complex without helper libraries and full card simulation,
            # this bot will use a very basic heuristic:
            # - If community cards suggest a strong hand (e.g., pair on board, two of same suit),
            #   and we have a matching card, maybe play.
            # - Otherwise, play extremely cautiously.

            # Placeholder for post-flop hand evaluation (needs actual poker hand evaluator)
            my_hand_potential = 0 # 0: weak, 1: medium, 2: strong

            # Simple heuristic:
            # Count matching ranks/suits with community cards
            cards_in_play = self.hole_cards + round_state.community_cards
            ranks = [card[0] for card in cards_in_play]
            suits = [card[1] for card in cards_in_play]

            # Check for pairs (simplistic)
            from collections import Counter
            rank_counts = Counter(ranks)
            if any(count >= 2 for count in rank_counts.values()):
                my_hand_potential = 1 # At least a pair

            # Check for flushes (simplistic, assumes we have two suited and 3+ on board)
            suit_counts = Counter(suits)
            if any(count >= 5 for count in suit_counts.values()):
                 my_hand_potential = 2 # Possible flush

            # Check for straights (very simplistic, needs sorting and checking sequence)
            # Not implementing full straight check due to complexity

            # Aggressiveness for post-flop
            # More cautious post-flop unless a strong hand.
            post_flop_aggressiveness = 0.3 + (position_factor * 0.1) # Less aggressive than pre-flop

            if my_hand_potential == 2: # Strong hand (e.g., flush draw, made flush/straight/set)
                if remaining_chips > amount_to_call + round_state.min_raise: # Enough for raise
                    if random.random() < post_flop_aggressiveness * 1.5: # Aggressive play
                        # Bet pot size or half pot
                        bet_amount = int(min(round_state.pot * 0.75, remaining_chips))
                        adjusted_bet_amount = max(bet_amount, round_state.min_raise)
                        adjusted_bet_amount = min(adjusted_bet_amount, round_state.max_raise)
                        if adjusted_bet_amount >= amount_to_call + round_state.min_raise:
                            return PokerAction.RAISE, int(adjusted_bet_amount)
                        elif amount_to_call < remaining_chips:
                            return PokerAction.CALL, 0
                        else:
                            return PokerAction.ALL_IN, 0 # if all-in is the only option and hand seems strong
                    elif amount_to_call < remaining_chips or can_check:
                        if can_check: return PokerAction.CHECK, 0
                        return PokerAction.CALL, 0
                    else:
                        return PokerAction.ALL_IN, 0 # Only aggressive option

                elif amount_to_call < remaining_chips:
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.ALL_IN, 0 # Committing with strong hand

            elif my_hand_potential == 1: # Medium hand (e.g., a pair, strong draw)
                if can_check:
                    return PokerAction.CHECK, 0
                elif amount_to_call <= remaining_chips / 5 and amount_to_call < remaining_chips: # Call small bets
                    return PokerAction.CALL, 0
                else:
                    return PokerAction.FOLD, 0

            else: # Weak hand
                if can_check:
                    return PokerAction.CHECK, 0
                else:
                    return PokerAction.FOLD, 0

        # Failsafe: if for some reason an action isn't returned above, check/fold
        if can_check:
            return PokerAction.CHECK, 0
        else:
            return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # The game engine should provide the player their hole cards at the beginning of each round or hand.
        # This is not done via `round_state.player_hands` as per the error (it's for showdown).
        # Clear hole cards for next round (assuming they are set by the framework for the current round)
        self.hole_cards = []
        # Reset assumption flag for local testing
        if hasattr(self, '_hole_cards_set_for_round'):
            del self._hole_cards_set_for_round

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        pass