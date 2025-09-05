from typing import List, Tuple
from bot import Bot
from type.poker_action import PokerAction
from type.round_state import RoundStateClient

class SimplePlayer(Bot):
    def __init__(self):
        super().__init__()
        self.player_hands = []
        self.starting_chips = 0
        self.blind_amount = 0
        self.big_blind_player_id = None
        self.small_blind_player_id = None
        self.all_players = []
        self.game_history = []

    def on_start(self, starting_chips: int, player_hands: List[str], blind_amount: int, big_blind_player_id: int, small_blind_player_id: int, all_players: List[int]):
        self.starting_chips = starting_chips
        self.player_hands = player_hands
        self.blind_amount = blind_amount
        self.big_blind_player_id = big_blind_player_id
        self.small_blind_player_id = small_blind_player_id
        self.all_players = all_players

    def on_round_start(self, round_state: RoundStateClient, remaining_chips: int):
        pass

    def get_action(self, round_state: RoundStateClient, remaining_chips: int) -> Tuple[PokerAction, int]:
        """ Returns the action for the player. """
        try:
            # Get current hand strength
            hand_strength = self._evaluate_hand_strength()
            
            # Get position info
            is_big_blind = str(self.id) == str(self.big_blind_player_id)
            is_small_blind = str(self.id) == str(self.small_blind_player_id)
            
            # Calculate pot odds and bet sizing
            call_amount = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
            pot_size = round_state.pot
            
            # Safety check for minimum raise
            min_raise_total = round_state.current_bet + round_state.min_raise
            my_current_bet = round_state.player_bets.get(str(self.id), 0)
            min_raise_amount = max(round_state.min_raise, min_raise_total - my_current_bet)
            
            # If we can't check and current bet is 0, we need to make a valid action
            if round_state.current_bet == 0:
                # We can check or bet
                if hand_strength >= 0.7:
                    # Strong hand - bet
                    bet_size = min(round_state.max_raise, max(round_state.min_raise, self.blind_amount * 2))
                    if bet_size > 0 and bet_size <= remaining_chips:
                        return (PokerAction.RAISE, bet_size)
                    else:
                        return (PokerAction.CHECK, 0)
                elif hand_strength >= 0.4:
                    # Medium hand - check
                    return (PokerAction.CHECK, 0)
                else:
                    # Weak hand - check and see flop cheaply
                    return (PokerAction.CHECK, 0)
            
            else:
                # There's a bet to us
                if call_amount >= remaining_chips:
                    # We'd be all-in to call
                    if hand_strength >= 0.6:
                        return (PokerAction.ALL_IN, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                
                # Calculate pot odds
                pot_odds = call_amount / (pot_size + call_amount + 0.001)  # Add small epsilon to avoid division by zero
                
                if hand_strength >= 0.8:
                    # Very strong hand - raise if possible
                    if min_raise_amount > 0 and min_raise_amount <= remaining_chips:
                        raise_size = min(min_raise_amount, remaining_chips, self.blind_amount * 3)
                        return (PokerAction.RAISE, raise_size)
                    else:
                        return (PokerAction.CALL, 0)
                        
                elif hand_strength >= 0.6:
                    # Good hand - call or small raise
                    if pot_odds < 0.3 and min_raise_amount > 0 and min_raise_amount <= remaining_chips:
                        raise_size = min(min_raise_amount, remaining_chips)
                        return (PokerAction.RAISE, raise_size)
                    else:
                        return (PokerAction.CALL, 0)
                        
                elif hand_strength >= 0.4:
                    # Marginal hand - call if pot odds are good
                    if pot_odds < 0.25:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
                        
                else:
                    # Weak hand - fold unless very good pot odds
                    if pot_odds < 0.15 and call_amount < self.blind_amount:
                        return (PokerAction.CALL, 0)
                    else:
                        return (PokerAction.FOLD, 0)
        
        except Exception as e:
            # Emergency fallback - make safest possible action
            if round_state.current_bet == 0:
                return (PokerAction.CHECK, 0)
            else:
                call_amount = max(0, round_state.current_bet - round_state.player_bets.get(str(self.id), 0))
                if call_amount <= self.blind_amount and call_amount <= remaining_chips:
                    return (PokerAction.CALL, 0)
                else:
                    return (PokerAction.FOLD, 0)

    def _evaluate_hand_strength(self) -> float:
        """Evaluate hand strength from 0.0 (worst) to 1.0 (best)"""
        if not self.player_hands or len(self.player_hands) < 2:
            return 0.3  # Default moderate strength
        
        try:
            card1, card2 = self.player_hands[0], self.player_hands[1]
            
            # Parse cards
            rank1, suit1 = self._parse_card(card1)
            rank2, suit2 = self._parse_card(card2)
            
            # High card values (Ace = 14, King = 13, etc.)
            high_card = max(rank1, rank2)
            low_card = min(rank1, rank2)
            
            # Pocket pairs
            if rank1 == rank2:
                if rank1 >= 10:  # JJ, QQ, KK, AA
                    return 0.9
                elif rank1 >= 7:  # 77, 88, 99, TT
                    return 0.7
                else:  # 22-66
                    return 0.6
            
            # Suited cards
            if suit1 == suit2:
                if high_card >= 12:  # Ace or King high suited
                    return 0.75
                elif high_card >= 10:  # Queen or Jack high suited
                    return 0.6
                else:
                    return 0.5
            
            # High cards
            if high_card == 14:  # Ace
                if low_card >= 10:  # AK, AQ, AJ, AT
                    return 0.8
                elif low_card >= 7:   # A9, A8, A7
                    return 0.6
                else:  # A6 and below
                    return 0.5
            
            if high_card == 13:  # King
                if low_card >= 10:  # KQ, KJ, KT
                    return 0.7
                elif low_card >= 7:  # K9, K8, K7
                    return 0.5
                else:
                    return 0.4
            
            # Connected cards
            if abs(rank1 - rank2) == 1:  # Connected
                if high_card >= 10:
                    return 0.6
                else:
                    return 0.45
            
            # Gapped connectors
            if abs(rank1 - rank2) == 2:  # One gap
                if high_card >= 10:
                    return 0.5
                else:
                    return 0.4
            
            # Face cards
            if high_card >= 11:  # Jack or better
                return 0.5
            
            # Low cards
            if high_card <= 8:
                return 0.2
            
            return 0.35  # Default for medium cards
            
        except Exception:
            return 0.3  # Safe default

    def _parse_card(self, card: str) -> Tuple[int, str]:
        """Parse card string like 'Ah' into rank (14) and suit ('h')"""
        if len(card) != 2:
            return 7, 'h'  # Default fallback
        
        rank_str, suit = card[0], card[1]
        
        rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                   '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        rank = rank_map.get(rank_str, 7)  # Default to 7 if unknown
        return rank, suit

    def on_end_round(self, round_state: RoundStateClient, remaining_chips: int):
        """ Called at the end of the round. """
        pass

    def on_end_game(self, round_state: RoundStateClient, player_score: float, all_scores: dict, active_players_hands: dict):
        """ Called at the end of the game. """
        pass