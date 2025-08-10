import collections
import itertools
import random
from typing import List, Tuple

from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    """
    A poker bot that plays a solid, fundamental-based strategy.
    - Pre-flop: Uses a hand-ranking system based on position to decide whether to play.
    - Post-flop: Uses a Monte Carlo simulation to estimate hand strength (equity).
    - Betting: Varies bet sizing based on hand strength and pot size.
    - Risk Management: Aims to be aggressive with strong hands and cautious with weak/mediocre hands.
    - This iteration fixes a critical bug where the bot would attempt to RAISE with an amount of 0,
      causing an invalid action and an automatic fold. It ensures all raise amounts are valid.
    """

    def __init__(self):
        super().__init__()
        self.hole_cards: List[str] = []
        self.all_players: List[int] = []
        self.starting_chips: int = 10000
        self.big_blind_amount: int = 0
        self.my_bet_in_round: int = 0
        # Monte Carlo sims - a balance between accuracy and the 30s time limit
        self.monte_carlo_sims: int = 250

    # --- Card and Hand Evaluation Helpers ---

    def _parse_card(self, card_str: str) -> Tuple[int, str]:
        """Parses a card string like 'Kh' into a tuple (rank, suit)."""
        rank_str = card_str[:-1]
        suit = card_str[-1].lower()
        vals = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        rank = vals.get(rank_str, int(rank_str))
        return (rank, suit)

    def _evaluate_5_card_hand(self, hand: List[Tuple[int, str]]):
        """
        Evaluates a 5-card hand and returns a tuple representing its rank.
        The tuple is structured (hand_rank, high_card_1, high_card_2, ...)
        to allow for easy comparison.
        """
        ranks = sorted([card[0] for card in hand], reverse=True)
        suits = [card[1] for card in hand]

        is_flush = len(set(suits)) == 1
        
        # Ace-low straight check: A,2,3,4,5 -> ranks are [14, 5, 4, 3, 2]
        is_straight = (len(set(ranks)) == 5 and (max(ranks) - min(ranks) == 4))
        is_ace_low_straight = ranks == [14, 5, 4, 3, 2]
        if is_ace_low_straight:
            is_straight = True
            # For ranking purposes, treat Ace as 1 in this specific straight
            ranks = [5, 4, 3, 2, 1]

        if is_straight and is_flush:
            return (8, *ranks)

        rank_counts = collections.Counter(sorted([card[0] for card in hand], reverse=True))
        major_ranks = sorted(rank_counts.keys(), key=lambda r: (rank_counts[r], r), reverse=True)
        count_vals = sorted(rank_counts.values(), reverse=True)

        if count_vals[0] == 4:
            return (7, *major_ranks)
        if count_vals == [3, 2]:
            return (6, *major_ranks)
        if is_flush:
            return (5, *sorted([card[0] for card in hand], reverse=True))
        if is_straight:
            return (4, *ranks)
        if count_vals[0] == 3:
            return (3, *major_ranks)
        if count_vals == [2, 2, 1]:
            return (2, *major_ranks)
        if count_vals[0] == 2:
            return (1, *major_ranks)
        return (0, *major_ranks)

    def _evaluate_best_hand(self, hole_cards: List[Tuple[int, str]], community_cards: List[Tuple[int, str]]):
        """Finds the best 5-card hand from a set of available cards."""
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            # Not enough cards to form a 5-card hand, should not happen post-flop
            return (-1,)

        best_hand_rank = (-1,)
        for hand_combination in itertools.combinations(all_cards, 5):
            current_rank = self._evaluate_5_card_hand(list(hand_combination))
            if current_rank > best_hand_rank:
                best_hand_rank = current_rank
        return best_hand_rank

    # --- Strategy Helpers ---

    def _calculate_hand_strength(self, round_state: RoundStateClient) -> float:
        """
        Estimates hand strength (win probability) using Monte Carlo simulation.
        """
        my_cards = [self._parse_card(c) for c in self.hole_cards]
        community = [self._parse_card(c) for c in round_state.community_cards]

        num_opponents = len([p_id for p_id in round_state.player_bets.keys() if int(p_id) != self.id])

        if num_opponents == 0:
            return 1.0

        deck = [(rank, suit) for rank in range(2, 15) for suit in "shdc"]
        
        for card in my_cards + community:
            if card in deck:
                deck.remove(card)

        wins = 0
        for _ in range(self.monte_carlo_sims):
            random.shuffle(deck)
            
            sim_deck = list(deck)
            opponents_hands = []
            try:
                for _ in range(num_opponents):
                    opponents_hands.append([sim_deck.pop(0), sim_deck.pop(0)])
                
                num_community_needed = 5 - len(community)
                sim_community = community + sim_deck[:num_community_needed]
            except IndexError:
                # Not enough cards in deck, can happen in rare cases. Skip sim.
                continue

            my_rank = self._evaluate_best_hand(my_cards, sim_community)
            
            is_winner = True
            for opp_hand in opponents_hands:
                opp_rank = self._evaluate_best_hand(opp_hand, sim_community)
                if opp_rank > my_rank:
                    is_winner = False
                    break
            if is_winner:
                wins += 1

        return wins / (self.monte_carlo_sims + 1e-9)

    def _get_preflop_hand_group(self) -> int:
        """Classifies a starting hand into a group (1=best, 5=worst) for pre-flop strategy."""
        card1, card2 = [self._parse_card(c) for c in self.hole_cards]
        rank1, suit1 = card1
        rank2, suit2 = card2

        is_suited = suit1 == suit2
        is_pair = rank1 == rank2
        high, low = max(rank1, rank2), min(rank1, rank2)

        if is_pair and high >= 10: return 1  # TT+
        if high == 14 and low >= 12: return 1  # AQ, AK
        if high == 13 and low == 12 and is_suited: return 1 # KQs

        if is_pair: return 2
        if high == 14: return 2
        if high >= 11 and is_suited: return 2

        if high >= 10 and low >= 8 and is_suited: return 3
        if high >= 12: return 3

        if is_suited: return 4
        if high >= 9 and low >= 7: return 4

        return 5

    # --- Bot API Methods ---
    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        """Called once at the start of each hand."""
        self.starting_chips = starting_chips
        self.hole_cards = player_hands
        self.big_blind_amount = blind_amount
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        """Called at the start of each betting round."""
        self.my_bet_in_round = round_state.player_bets.get(str(self.id), 0)

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Main decision-making function. """
        self.my_bet_in_round = round_state.player_bets.get(str(self.id), 0)
        can_check = round_state.current_bet == self.my_bet_in_round
        amount_to_call = round_state.current_bet - self.my_bet_in_round

        # --- Pre-flop Strategy ---
        if round_state.round == 'Preflop':
            group = self._get_preflop_hand_group()

            raise_amount = 0
            if group <= 2:  # Premium and strong hands
                # If there's a raise already, reraise. Otherwise, open raise.
                if round_state.current_bet > self.big_blind_amount:
                    raise_amount = round_state.current_bet * 2.5
                else:
                    raise_amount = self.big_blind_amount * 3
            elif group == 3: # Decent playable hands
                if round_state.current_bet <= self.big_blind_amount * 2:
                    raise_amount = self.big_blind_amount * 2.5
                else: # Don't want to play against big aggression
                    return PokerAction.FOLD, 0
            else: # Speculative/weak hands
                if can_check:
                    return PokerAction.CHECK, 0
                if amount_to_call <= self.big_blind_amount:
                    return PokerAction.CALL, 0
                return PokerAction.FOLD, 0
            
            if raise_amount > 0:
                final_raise = max(raise_amount, round_state.min_raise)
                final_raise = min(final_raise, round_state.max_raise)
                if final_raise > amount_to_call:
                     return PokerAction.RAISE, int(final_raise)
            
            return PokerAction.CALL, 0 if not can_check else PokerAction.CHECK, 0

        # --- Post-flop Strategy (Flop, Turn, River) ---
        hand_strength = self._calculate_hand_strength(round_state)
        pot_odds = amount_to_call / (round_state.pot + amount_to_call + 1e-9) if amount_to_call > 0 else 0

        raise_amount = 0
        if hand_strength > 0.85: # Nuts or very close
            raise_amount = int(round_state.pot * 0.8) # Value town
        elif hand_strength > 0.65: # Strong made hand
            raise_amount = int(round_state.pot * 0.6) # Value bet
        elif hand_strength > 0.45 and round_state.round != 'River': # Decent made hand or strong draw
             # Check/call mostly, but bet if checked to.
             if can_check:
                 raise_amount = int(round_state.pot * 0.4)
             else:
                 # If facing a bet, just call if odds are good
                 if hand_strength > pot_odds:
                     return PokerAction.CALL, 0
                 else:
                     return PokerAction.FOLD, 0
        else: # Weak hand or busted draw
            if can_check:
                return PokerAction.CHECK, 0
            if hand_strength > pot_odds and amount_to_call < round_state.pot * 0.2:
                 # Call small bets with some equity
                return PokerAction.CALL, 0
            return PokerAction.FOLD, 0
        
        # --- Action validation and execution ---
        if raise_amount > 0:
            # THIS IS THE CRITICAL FIX: Ensure raise amount is valid.
            final_raise = max(raise_amount, round_state.min_raise)
            final_raise = min(final_raise, round_state.max_raise)
            
            # The raise amount is the *additional* chips to put in.
            # Make sure it's a valid raise over the current bet.
            if self.my_bet_in_round + final_raise > round_state.current_bet:
                return PokerAction.RAISE, int(final_raise)

        # Fallback logic if raise is not possible or desirable
        if can_check:
            return PokerAction.CHECK, 0
        if hand_strength > pot_odds:
            return PokerAction.CALL, 0
        return PokerAction.FOLD, 0

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of a betting round. Can be used for opponent modeling. """
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """ Called at the end of the hand. Can be used for logging or analysis. """
        pass