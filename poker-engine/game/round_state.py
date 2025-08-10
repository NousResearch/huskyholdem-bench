from poker_type.game import PokerAction
from typing import List, Dict, Set
from dataclasses import dataclass
import time

@dataclass
class ActionRecord:
    """Represents a single action taken by a player"""
    player_id: int
    action: PokerAction
    amount: int
    timestamp: int
    # Round-specific pot information
    pot_after_action: int
    side_pots_after_action: List[Dict]
    # Cumulative pot information across all rounds
    total_pot_after_action: int
    total_side_pots_after_action: List[Dict]
    
@dataclass
class Pot:
    """Represents a single pot (main pot or side pot)"""
    amount: int
    eligible_players: Set[int]  # Players who can win this pot
    
    def __init__(self, amount: int = 0, eligible_players: Set[int] = None):
        self.amount = amount
        self.eligible_players = eligible_players if eligible_players else set()

class RoundState:
    def __init__(self, active_players: List[int]):
        self.pots: List[Pot] = [Pot(0, set(active_players))]  # Start with main pot
        self.raise_amount = 0
        self.bettor = None
        self.waiting_for: Set[int] = set(active_players)
        self.player_bets: Dict[int, int] = {player: 0 for player in active_players}
        self.player_actions: Dict[int, PokerAction] = {}  # Keep for backward compatibility
        self.action_history: List[ActionRecord] = []  # New: track all actions in order
        self.all_in_players: Set[int] = set()  # Track all-in players
        self.player_action_times: Dict[int, int] = {}
        
        # Cumulative pot tracking
        self.cumulative_pot_base = 0
        self.cumulative_side_pots_base = []

    def set_cumulative_pot_info(self, cumulative_pot: int, cumulative_side_pots: List[Dict]):
        """Set the cumulative pot information from previous rounds"""
        self.cumulative_pot_base = cumulative_pot
        self.cumulative_side_pots_base = cumulative_side_pots

    def get_total_pot_info(self) -> Dict:
        """Get total cumulative pot information including current round"""
        current_round_pot = self.pot
        total_pot = self.cumulative_pot_base + current_round_pot
        
        # Merge current round side pots with cumulative side pots
        current_side_pots = self.get_side_pots_info()
        total_side_pots = self.cumulative_side_pots_base.copy()
        
        # Add current round side pots with unique IDs
        next_id = len(self.cumulative_side_pots_base)
        for i, side_pot in enumerate(current_side_pots):
            total_side_pots.append({
                "id": next_id + i,
                "amount": side_pot["amount"],
                "eligible_players": side_pot["eligible_players"]
            })
        
        return {
            "total_pot": total_pot,
            "total_side_pots": total_side_pots
        }
    
    @property
    def pot(self) -> int:
        """Total pot amount across all pots (for backward compatibility)"""
        return sum(pot.amount for pot in self.pots)
    
    def get_pot_and_side_pots_info(self) -> Dict:
        """Get current pot and side pot information"""
        side_pots_info = self.get_side_pots_info()
        return {
            "total_pot": self.pot,
            "side_pots": side_pots_info
        }
    
    def __str__(self):
        pots_str = ", ".join([f"Pot {i}: {pot.amount} (players: {pot.eligible_players})" for i, pot in enumerate(self.pots)])
        return f"\tPots: [{pots_str}] \n\t Raise Amount: {self.raise_amount} \n\t Bettor: {self.bettor} \n\t Waiting For: {self.waiting_for} \n\t Player Bets: {self.player_bets} \n\t Player Actions: {self.player_actions} \n\t All-in Players: {self.all_in_players}"

    def print_debug(self):
        pots_str = ", ".join([f"Pot {i}: {pot.amount} (players: {pot.eligible_players})" for i, pot in enumerate(self.pots)])
        s = f"Pots: [{pots_str}] \n Raise Amount: {self.raise_amount} \n Bettor: {self.bettor} \n Waiting For: {self.waiting_for} \n Player Bets: {self.player_bets} \n Player Actions: {self.player_actions} \n All-in Players: {self.all_in_players}"
        print(s)

    def _create_side_pots(self):
        """Create side pots when players have unequal investments"""
        # Get all active players (not folded) - these are eligible to win pots
        active_players = set()
        for player_id, action in self.player_actions.items():
            if action != PokerAction.FOLD:
                active_players.add(player_id)
        
        if len(active_players) <= 1:
            # Still create pots even with 1 or 0 active players (folded players contribute)
            total_pot = sum(self.player_bets.values())
            if len(active_players) == 1:
                self.pots = [Pot(total_pot, active_players)]
            else:
                # All players folded - money goes nowhere, but we need to track it
                self.pots = [Pot(total_pot, set())]
            return
        
        # Get unique bet levels in ascending order (from ALL players, including folded)
        bet_levels = sorted(set(bet for bet in self.player_bets.values() if bet > 0))
        
        if len(bet_levels) <= 1:
            # All players bet the same amount
            total_pot = sum(self.player_bets.values())
            self.pots = [Pot(total_pot, active_players)]
            return
        
        # Clear existing pots and recreate them
        self.pots = []
        
        # Create pots for each betting level
        for i, current_level in enumerate(bet_levels):
            prev_level = bet_levels[i-1] if i > 0 else 0
            level_contribution = current_level - prev_level
            
            # Find players who contributed to this level (bet >= current_level)
            # Count ALL players who bet at this level, including folded ones
            eligible_players = set()
            contributing_count = 0
            for player_id, bet_amount in self.player_bets.items():
                if bet_amount >= current_level:
                    contributing_count += 1
                    # Only active players are eligible to win
                    if player_id in active_players:
                        # CRITICAL FIX: All-in players from previous rounds should only be eligible
                        # for pots up to their all-in amount, not for pots created by subsequent betting
                        if player_id in self.all_in_players:
                            # Check if this player went all-in in a previous round
                            # and if so, only include them if this pot level doesn't exceed their all-in amount
                            all_in_amount = self.player_bets[player_id]
                            if current_level <= all_in_amount:
                                eligible_players.add(player_id)
                        else:
                            # Non-all-in players are eligible for all pots
                            eligible_players.add(player_id)
            
            if contributing_count > 0 and level_contribution > 0:
                pot_amount = level_contribution * contributing_count
                self.pots.append(Pot(pot_amount, eligible_players))
        
        # If no pots were created, create a single main pot
        if len(self.pots) == 0:
            total_pot = sum(self.player_bets.values())
            self.pots = [Pot(total_pot, active_players)]

    def _update_waiting_for_after_raise(self, player_id: int) -> None:
        self.waiting_for = set(p for p in self.player_bets.keys() if p != player_id)
        for player in self.waiting_for.copy():
            if player in self.player_actions and self.player_actions[player] in [PokerAction.FOLD, PokerAction.ALL_IN]:
                self.waiting_for.discard(player)
            else:
                self.player_actions[player] = None

    def post_forced_blind(self, player_id: int, action: PokerAction, amount: int = 0) -> None:
        """Post a forced blind without affecting the waiting_for logic like a normal raise would"""
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        self.player_actions[player_id] = action
        
        # For forced blinds, we don't check if player is in waiting_for
        # and we don't modify waiting_for here
        
        if action == PokerAction.RAISE:
            # Update the bet amount and raise amount
            self.player_bets[player_id] += amount
            if self.player_bets[player_id] > self.raise_amount:
                self.raise_amount = self.player_bets[player_id]
                self.bettor = player_id
            # NOTE: We don't call _update_waiting_for_after_raise for forced blinds
        
        # Update pots after blind posting
        self._update_pots()
        
        # Record this action in history
        round_pot_info = self.get_pot_and_side_pots_info()
        total_pot_info = self.get_total_pot_info()
        
        action_record = ActionRecord(
            player_id=player_id,
            action=action,
            amount=amount,
            timestamp=int(time.time() * 1000),
            pot_after_action=round_pot_info["total_pot"],
            side_pots_after_action=round_pot_info["side_pots"],
            total_pot_after_action=total_pot_info["total_pot"],
            total_side_pots_after_action=total_pot_info["total_side_pots"]
        )
        self.action_history.append(action_record)

    def add_blind_players_for_second_action(self, small_blind_player: int, big_blind_player: int) -> None:
        """Add blind players back for their second action after all other players have acted"""
        # Only add them if they haven't folded or gone all-in
        if (small_blind_player in self.player_actions and 
            self.player_actions[small_blind_player] not in [PokerAction.FOLD, PokerAction.ALL_IN]):
            self.waiting_for.add(small_blind_player)
            
        if (big_blind_player in self.player_actions and 
            self.player_actions[big_blind_player] not in [PokerAction.FOLD, PokerAction.ALL_IN]):
            self.waiting_for.add(big_blind_player)

    def update_player_action(self, player_id: int, action: PokerAction, amount: int = 0) -> None:
        """Update the round state based on a player's action"""

        if amount < 0:
            raise ValueError("Amount cannot be negative")

        self.player_actions[player_id] = action

        if player_id not in self.waiting_for:
            raise ValueError("Player is not waiting for their turn")

        actual_amount = 0  # Track the actual amount bet/called for logging
        
        if action == PokerAction.FOLD:
            self.waiting_for.discard(player_id)
            self.player_actions[player_id] = PokerAction.FOLD
        elif action == PokerAction.CHECK:
            # Special case: Big blind can check if they are the bettor but no one raised above their blind
            # This happens when big blind posted their blind and no one raised above it
            can_check = (self.bettor is None or 
                        (self.bettor == player_id and 
                         self.player_bets[player_id] == self.raise_amount))
            
            if not can_check:
                raise ValueError("Cannot check when there has been a raise")
            self.waiting_for.discard(player_id)
            self.player_actions[player_id] = PokerAction.CHECK
        elif action == PokerAction.CALL:
            """
            Call the current raise amount, the amount is the difference between the
            current raise amount and the player's current bet. 
            input amount doesn't matter
            """
            call_amount = self.raise_amount - self.player_bets[player_id]
            if call_amount < 0:
                raise ValueError("Cannot call with less than the raise amount")
            self.player_bets[player_id] += call_amount
            actual_amount = call_amount
            self.waiting_for.discard(player_id)
            self.player_actions[player_id] = PokerAction.CALL
        elif action == PokerAction.ALL_IN:
            self.player_bets[player_id] += amount
            actual_amount = amount
            self.all_in_players.add(player_id)
            self.waiting_for.discard(player_id)
            self.player_actions[player_id] = PokerAction.ALL_IN
            if self.player_bets[player_id] > self.raise_amount:
                self.raise_amount = self.player_bets[player_id]
                self.bettor = player_id
                self._update_waiting_for_after_raise(player_id)
        elif action == PokerAction.RAISE:
            if amount + self.player_bets[player_id] <= self.raise_amount:
                print(f"Raise amount: {amount + self.player_bets[player_id]} <= {self.raise_amount}")
                raise ValueError("Raise amount + current bet must be higher than the current raise")
            self.raise_amount = self.player_bets[player_id] + amount
            self.bettor = player_id
            self.player_bets[player_id] += amount
            actual_amount = amount
            self.waiting_for = set(p for p in self.player_bets.keys() if p != player_id)
            self._update_waiting_for_after_raise(player_id)
        
        # Update pots after any action that changes bet amounts
        self._update_pots()
        
        # Get round-specific pot information
        round_pot_info = self.get_pot_and_side_pots_info()
        
        # Get total cumulative pot information
        total_pot_info = self.get_total_pot_info()
        
        # Record this action in history with both round-specific and cumulative info
        action_record = ActionRecord(
            player_id=player_id,
            action=action,
            amount=actual_amount,
            timestamp=int(time.time() * 1000),
            # Round-specific pot information
            pot_after_action=round_pot_info["total_pot"],
            side_pots_after_action=round_pot_info["side_pots"],
            # Cumulative pot information across all rounds
            total_pot_after_action=total_pot_info["total_pot"],
            total_side_pots_after_action=total_pot_info["total_side_pots"]
        )
        self.action_history.append(action_record)

    def _update_pots(self):
        """Update pot amounts based on current player bets"""
        # Always try to create side pots when there are unequal bet amounts
        bet_amounts = [amount for amount in self.player_bets.values() if amount > 0]
        if len(set(bet_amounts)) > 1:
            # Unequal bet amounts - create side pots
            self._create_side_pots()
        else:
            # Equal bet amounts - use simple pot calculation
            total_contributed = sum(self.player_bets.values())
            if len(self.pots) == 1:
                self.pots[0].amount = total_contributed
            else:
                # Reset to single pot
                active_players = set()
                for player_id, action in self.player_actions.items():
                    if action != PokerAction.FOLD:
                        active_players.add(player_id)
                self.pots = [Pot(total_contributed, active_players)]

    def is_round_complete(self) -> bool:
        """Check if the current round is complete"""
        if len(self.waiting_for) == 0:
            # Create final side pots when round is complete
            self._create_side_pots()
            return True
        return False

    def reset_for_next_round(self, active_players: List[int]) -> None:
        """Reset the round state for a new round"""
        # Keep track of players who are still all-in from previous rounds
        still_all_in = self.all_in_players.intersection(set(active_players))
        
        self.pots = [Pot(0, set(active_players))]
        self.raise_amount = 0
        self.bettor = None
        self.waiting_for = set(active_players) - still_all_in  # All-in players don't act
        self.player_bets = {player: 0 for player in active_players}
        self.player_actions = {}
        self.action_history = []  # Clear action history for new round
        self.all_in_players = still_all_in
        self.player_action_times = {}

    def get_current_player(self) -> Set[int]:
        """Get the current player in the round"""
        if len(self.waiting_for) == 0:
            return set()
        return self.waiting_for

    def get_side_pots_info(self) -> List[Dict]:
        """Get information about all pots for display purposes"""
        return [
            {
                "amount": pot.amount,
                "eligible_players": list(pot.eligible_players)
            }
            for pot in self.pots
        ]