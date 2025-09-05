from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient
import random

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.starting_chips = 0
        self.blind_amount = 0
        self.big_blind_player_id = None
        self.small_blind_player_id = None
        self.all_players = []
        self.hole_cards = []
        self.current_round = None
        self.position = 0  # Relative position: 0 = Early, 1 = Middle, 2 = Late (button)
        self.opp_stats = {}  # Track opponent tendencies: {player_id: {folds_to_cbet: float, aggr_prob: float, ...}}
        self.hand_strength_estimate = 0.0
        self.previous_bet = 0

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players
        self.hole_cards = player_hands
        # Initialize opponent stats
        for pid in all_players:
            self.opp_stats[pid] = {
                'total_postflop_actions': 0,
                'folds_to_cbet': 0,
                'calls_or_raises': 0,
                'aggressive_actions': 0
            }

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        self.current_round = round_state.round
        current_player_index = round_state.current_player.index(self.id) if self.id in round_state.current_player else -1
        num_players = len(round_state.current_player)
        if num_players > 0:
            self.position = (num_players - current_player_index)  # Later index = later position
        else:
            self.position = 0
        # Estimate hand strength on round start
        self.hand_strength_estimate = self.estimate_hand_strength(
            self.hole_cards, round_state.community_cards
        )

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        try:
            current_bet = round_state.current_bet
            pot = round_state.pot
            min_raise = round_state.min_raise
            max_raise = min(remaining_chips, round_state.max_raise)
            my_current_bet = round_state.player_bets.get(str(self.id), 0)
            to_call = current_bet - my_current_bet

            # If all players have checked, we can check
            if to_call == 0:
                return (PokerAction.CHECK, 0)

            # If we cannot call, we must fold or go all-in
            if to_call >= remaining_chips:
                # Can't call without going all-in
                if self.hand_strength_estimate > 0.5:
                    return (PokerAction.ALL_IN, remaining_chips)
                else:
                    # Fold if hand is weak
                    return (PokerAction.FOLD, 0)

            # Get number of active players
            active_players = len([pid for pid, bet in round_state.player_bets.items() if bet > -1])

            # Pre-flop strategy
            if round_state.round == 'Preflop':
                action, amount = self.pre_flop_strategy(
                    self.hole_cards, to_call, pot, remaining_chips, 
                    round_state.small_blind_player_id, round_state.big_blind_player_id,
                    active_players, self.position
                )
            else:
                # Post-flop: use hand strength and board texture
                action, amount = self.post_flop_strategy(
                    to_call, pot, remaining_chips, min_raise, max_raise, active_players, round_state
                )

            # Validate raise amount
            if action == PokerAction.RAISE:
                if amount <= current_bet:
                    amount = min_raise  # Ensure at least min_raise over current bet
                amount = min(amount, max_raise)
                if amount < min_raise:
                    # Cannot make a legal raise, fallback to call or fold
                    if self.hand_strength_estimate > 0.4:
                        return (PokerAction.CALL, to_call)
                    else:
                        return (PokerAction.FOLD, 0)
                return (action, amount)

            # Fallback: Call if we can't do better
            if action in [PokerAction.CALL, PokerAction.ALL_IN] and amount > remaining_chips:
                return (PokerAction.ALL_IN, remaining_chips)

            return (action, amount)

        except Exception as e:
            # On any error, fold to avoid crash
            return (PokerAction.FOLD, 0)

    def pre_flop_strategy(self, hole_cards: List[str], to_call: int, pot: int, remaining_chips: int,
                          small_blind_id: int, big_blind_id: int, active_players: int, position: int) -> Tuple[PokerAction, int]:
        # Evaluate hole cards strength (simplified)
        rank1, suit1 = hole_cards[0][0], hole_cards[0][1]
        rank2, suit2 = hole_cards[1][0], hole_cards[1][1]
        rank_order = "23456789TJQKA"
        r1 = rank_order.index(rank1)
        r2 = rank_order.index(rank2)
        
        # Pocket pairs
        if rank1 == rank2:
            if r1 >= 10:  # JJ, QQ, KK, AA
                raise_amount = min(3 * to_call + self.blind_amount, remaining_chips)
                return (PokerAction.RAISE, raise_amount) if to_call > 0 else (PokerAction.RAISE, self.blind_amount * 3)
            elif r1 >= 6:  # 77-TT
                if to_call <= self.blind_amount * 3:
                    return (PokerAction.CALL, to_call)
                else:
                    return (PokerAction.FOLD, 0)
            else:
                if to_call == self.blind_amount and position >= 2:  # Call from late if no raise
                    return (PokerAction.CALL, to_call)
                else:
                    return (PokerAction.FOLD, 0)

        # Suited connectors / broadways
        suited = suit1 == suit2
        connected = abs(r1 - r2) == 1
        connector_high = (abs(r1 - r2) == 1 and max(r1, r2) >= 9)
        broadway = r1 >= 9 and r2 >= 9

        if suited and connector_high:
            if to_call <= self.blind_amount * 3:
                return (PokerAction.CALL, to_call)
            else:
                return (PokerAction.FOLD, 0)
        elif suited and broadway:
            if to_call <= self.blind_amount * 4:
                return (PokerAction.CALL, to_call)
            elif to_call == 0:
                return (PokerAction.RAISE, self.blind_amount * 3)
            else:
                return (PokerAction.FOLD, 0)
        elif broadway:
            if to_call <= self.blind_amount * 2:
                return (PokerAction.CALL, to_call)
            else:
                return (PokerAction.FOLD, 0)
        else:
            # Weak hands
            if to_call == 0:
                return (PokerAction.CHECK, 0)
            elif self.id == big_blind_id and to_call == self.blind_amount:
                return (PokerAction.CALL, to_call)
            else:
                return (PokerAction.FOLD, 0)

    def post_flop_strategy(self, to_call: int, pot: int, remaining_chips: int,
                           min_raise: int, max_raise: int, active_players: int, round_state: RoundStateClient) -> Tuple[PokerAction, int]:
        try:
            equity = self.hand_strength_estimate
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0.0

            # Bluffing and aggression factor
            aggression_factor = 0.5
            if active_players > 2:
                aggression_factor = 0.3  # Tighter in multi-way
            elif active_players == 2:
                aggression_factor = 0.6

            # Expected Value Decision
            if equity >= pot_odds:
                if equity > 0.7:
                    # Strong hand: raise for value
                    raise_size = min(int(pot * 0.75), max_raise)
                    if raise_size < min_raise:
                        return (PokerAction.CALL, to_call)
                    return (PokerAction.RAISE, raise_size)
                elif equity > 0.5:
                    # Decent hand: call or small raise
                    if random.random() < aggression_factor and to_call > 0:
                        raise_size = min(int(pot * 0.5), max_raise)
                        if raise_size >= min_raise:
                            return (PokerAction.RAISE, raise_size)
                    return (PokerAction.CALL, to_call)
                else:
                    # Weak hand, but equity higher than pot odds: call on draw
                    if self.is_draw_hand(round_state.community_cards, self.hole_cards):
                        # Pot odds support draw
                        if pot_odds <= 0.25 and equity >= 0.15:
                            return (PokerAction.CALL, to_call)
                        else:
                            # Semi-bluff raise?
                            if random.random() < 0.3 and min_raise <= max_raise:
                                return (PokerAction.RAISE, min(int(pot * 0.5), max_raise))
                    return (PokerAction.CALL, to_call)
            else:
                # Fold if equity < pot odds, unless bluffing opportunity
                if self.can_bluff_opportunity(round_state) and random.random() < 0.2:
                    bluff_raise = min(int(pot * 0.75), max_raise)
                    if bluff_raise >= min_raise:
                        return (PokerAction.RAISE, bluff_raise)
                return (PokerAction.FOLD, 0)
        except:
            return (PokerAction.FOLD, 0)

    def is_draw_hand(self, community_cards: List[str], hole_cards: List[str]) -> bool:
        # Simple heuristic: check for flush or straight draw
        all_cards = hole_cards + community_cards
        ranks = [card[0] for card in all_cards]
        suits = [card[1] for card in all_cards]

        # Flush draw: 4 cards of same suit
        for suit in 'shcd':
            if suits.count(suit) >= 4:
                return True

        # Straight draw: two common sequences
        rank_order = "23456789TJQKA"
        rank_indices = sorted([rank_order.index(r) for r in ranks])
        unique_ranks = sorted(set(rank_indices))
        for i in range(len(unique_ranks) - 3):
            if unique_ranks[i+3] - unique_ranks[i] <= 4:
                return True

        return False

    def can_bluff_opportunity(self, round_state: RoundStateClient) -> bool:
        # Bluff if board is scary and opponents may fold
        community_cards = round_state.community_cards
        if len(community_cards) < 3:
            return False
        # Check for flush potential or connected board
        suits = [card[1] for card in community_cards]
        if max([suits.count(s) for s in 'shcd']) >= 3:
            return True  # Flush board
        # Check straights
        rank_order = "23456789TJQKA"
        ranks = [card[0] for card in community_cards]
        indices = sorted([rank_order.index(r) for r in ranks])
        for i in range(len(indices) - 2):
            if indices[i+2] - indices[i] <= 4:
                return True
        return False

    def estimate_hand_strength(self, hole_cards: List[str], community_cards: List[str]) -> float:
        # Crude hand strength estimator (0 to 1)
        if not community_cards:
            # Pre-flop strength based on hole cards
            card1, card2 = hole_cards[0], hole_cards[1]
            r1, s1 = card1[0], card1[1]
            r2, s2 = card2[0], card2[1]
            rank_order = "23456789TJQKA"
            v1 = rank_order.index(r1)
            v2 = rank_order.index(r2)

            if r1 == r2:
                return 0.2 + min(v1, 12) * 0.06  # Pocket pairs: 22 ~ 0.2, AA ~ 0.92
            elif s1 == s2:
                if abs(v1 - v2) == 1:
                    return 0.15 + max(v1, v2) * 0.02  # Suited connectors
                elif max(v1, v2) >= 10:
                    return 0.1 + min(v1, v2) * 0.02  # Suited broadways
            elif abs(v1 - v2) == 1:
                return 0.1 + max(v1, v2) * 0.015  # Offsuit connectors
            elif max(v1, v2) >= 10:
                return 0.08 + min(v1, v2) * 0.015  # Offsuit broadways
            else:
                return 0.02 + (v1 + v2) * 0.005
        else:
            # Post-flop: simulate hand evaluation (very simple)
            try:
                all_cards = hole_cards + community_cards
                ranks = [card[0] for card in all_cards]
                suits = [card[1] for card in all_cards]

                # Count pairs, etc.
                rank_count = {r: ranks.count(r) for r in set(ranks)}
                pair_count = sum(1 for count in rank_count.values() if count >= 2)
                three_kind = sum(1 for count in rank_count.values() if count >= 3)
                four_kind = sum(1 for count in rank_count.values() if count >= 4)

                flush = max(suits.count(s) for s in 'shcd') >= 5
                straight = self.has_straight(ranks)

                if four_kind:
                    return 0.95
                elif three_kind and pair_count >= 2:
                    return 0.88
                elif flush:
                    return 0.8
                elif straight:
                    return 0.7
                elif three_kind:
                    return 0.6
                elif pair_count == 2:
                    return 0.4
                elif pair_count == 1:
                    return 0.25 + max([rank_order.index(r) for r, c in rank_count.items() if c >=2]) * 0.02
                else:
                    # High card
                    top_rank = max([rank_order.index(r) for r in ranks])
                    return 0.05 + top_rank * 0.03
            except:
                return 0.1

    def has_straight(self, ranks: List[str]) -> bool:
        rank_order = "23456789TJQKA"
        unique_ranks = sorted(set([rank_order.index(r) for r in ranks]))
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i+4] - unique_ranks[i] == 4:
                return True
        # Check for A-5 straight
        if set('A2345') <= set(ranks):
            return True
        return False

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        # Update opponent stats if possible (e.g. if they folded on flop)
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        # Game ended; reset or store data if needed
        self.hole_cards = []
        self.current_round = None
        self.hand_strength_estimate = 0.0
        self.previous_bet = 0
        # Could log results or refine model if persistence was allowed