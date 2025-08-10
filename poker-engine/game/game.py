from typing import Tuple, Set, Dict, List

import eval7
from config import NUM_ROUNDS
from deck import PokerDeck
from game.round_state import RoundState
from poker_type.game import PokerRound, PokerAction
from poker_type.messsage import GameStateMessage
from poker_type.utils import get_poker_action_name_from_enum, get_round_name
from config import BASE_PATH
import time
import os
import json
import uuid

GAME_ROUNDS = [PokerRound.PREFLOP, PokerRound.FLOP, PokerRound.TURN, PokerRound.RIVER]

class Game:
    def __init__(self, debug: bool = False, blind_amount: int = 10, game_sequence: int = None, game_id: str = None):
        self.debug = debug
        self.nums_round = NUM_ROUNDS
        self.players: List[int] = []
        self.active_players: List[int] = []
        self.deck = PokerDeck()
        self.hands: Dict[int, List[eval7.Card]] = {}
        self.board: List[str] = []
        self.round_index = -1
        self.total_pot = 0
        self.historical_pots: List[int] = []
        self.player_history: Dict = {}
        self.current_round: RoundState = None
        self.score = {}
        self.is_running = False
        self.game_start_time = 0
        self.game_sequence = game_sequence  # Store the game sequence number
        self.simulation_game_id = game_id  # Store the shared game ID for simulation
        
        # Blind functionality
        self.blind_amount = blind_amount
        self.small_blind_player = None
        self.big_blind_player = None
        self.dealer_button_position = 0  # This will be set by the server
        self.blind_players_added_back = False  # Track if blind players got their second action
        
        # Player money tracking
        self.player_starting_money: Dict[int, int] = {}  # Starting money for each player
        self.player_final_money: Dict[int, int] = {}     # Final money for each player
        self.player_delta: Dict[int, int] = {}           # Delta/gain for each player
        self.initial_money: int = 0                      # Initial money amount

        self.json_game_log = {
            "rounds": {},
            "playerNames": {},
            "playerHands": {},
            "finalBoard": [],
            "blinds": {},
            "sidePots": [],
        }

    def set_blind_amount(self, amount: int):
        """Set the blind amount for the game"""
        self.blind_amount = amount

    def get_blind_amount(self):
        """Get the current blind amount"""
        return self.blind_amount

    def get_small_blind_player(self):
        """Get the current small blind player"""
        return self.small_blind_player

    def get_big_blind_player(self):
        """Get the current big blind player"""
        return self.big_blind_player

    def set_dealer_button_position(self, position: int):
        """Set the dealer button position (called by server)"""
        self.dealer_button_position = position

    def assign_blinds(self):
        """Assign small and big blind players based on dealer button position"""
        if len(self.active_players) < 2:
            return
        
        if len(self.active_players) == 2:
            # In heads-up, dealer is small blind
            self.small_blind_player = self.active_players[self.dealer_button_position % len(self.active_players)]
            self.big_blind_player = self.active_players[(self.dealer_button_position + 1) % len(self.active_players)]
        else:
            # In multi-player, small blind is to the left of dealer, big blind is to the left of small blind
            self.small_blind_player = self.active_players[(self.dealer_button_position + 1) % len(self.active_players)]
            self.big_blind_player = self.active_players[(self.dealer_button_position + 2) % len(self.active_players)]

    def assign_blinds_with_money_check(self, player_money: Dict[int, int], blind_amount: int):
        """
        Assign small and big blind players based on dealer button position and player money.
        Skip players who can't afford the big blind and assign to the first players who can afford it.
        Returns a list of players who were forced to fold due to insufficient money.
        """
        if len(self.active_players) < 2:
            return []
        
        forced_fold_players = []
        big_blind_amount = blind_amount
        
        # Get all players in order starting from dealer button position
        all_players = self.players.copy()
        num_players = len(all_players)
        
        # First pass: remove players who can't afford the big blind
        players_to_remove = []
        for player_id in self.active_players:
            if player_money.get(player_id, 0) < big_blind_amount:
                players_to_remove.append(player_id)
        
        for player_id in players_to_remove:
            forced_fold_players.append(player_id)
            self.active_players.remove(player_id)
        
        # If we don't have enough players after removing those who can't afford big blind
        if len(self.active_players) < 2:
            return forced_fold_players
        
        # Find small blind player (first player who can afford big blind)
        small_blind_player = None
        for i in range(num_players):
            player_pos = (self.dealer_button_position + i) % num_players
            player_id = all_players[player_pos]
            if player_id in self.active_players:
                small_blind_player = player_id
                break
        
        # Find big blind player (next player who can afford big blind)
        big_blind_player = None
        for i in range(num_players):
            player_pos = (self.dealer_button_position + i) % num_players
            player_id = all_players[player_pos]
            if player_id in self.active_players and player_id != small_blind_player:
                big_blind_player = player_id
                break
        
        # Assign the blind players
        self.small_blind_player = small_blind_player
        self.big_blind_player = big_blind_player
        
        return forced_fold_players

    # def post_blinds(self):
    #     """Automatically post the blinds for small and big blind players"""
    #     if self.small_blind_player and self.big_blind_player:
    #         # Post small blind
    #         self.current_round.update_player_action(
    #             self.small_blind_player, 
    #             PokerAction.RAISE, 
    #             self.blind_amount // 2
    #         )
            
    #         # Post big blind
    #         self.current_round.update_player_action(
    #             self.big_blind_player, 
    #             PokerAction.RAISE, 
    #             self.blind_amount
    #         )

    def assign_player_ids_hand(self, player_id: int, hand: List[str]):
        """
        Assign a hand to a player. This is only used for testing purposes.
        In a real game, the hands are dealt by the deck.
        """
        if not self.debug:
            return

        if player_id not in self.players:
            raise ValueError("Player ID not found in the game")
        self.hands[player_id] = hand

    def assign_board(self, board: List[str]):
        """
        Assign a board to the game. This is only used for testing purposes.
        In a real game, the board is dealt by the deck.
        """
        if not self.debug:
            return

        self.board = board

    def add_player(self, player_id: int):
        self.players.append(player_id)
        self.active_players.append(player_id)

    def get_active_players(self):
        return self.active_players
    
    def get_player_hands(self, player_id: int):
        return self.hands[player_id]

    def print_debug(self):
        if self.debug:
            s = f"Players: {self.players} \n Active Players: {self.active_players} \n Hands: {self.hands} \n Board: {self.board} \n Round Index: {self.round_index} \n Total Pot: {self.total_pot} \n Historical Pots: {self.historical_pots} \n Player History: {self.player_history} \n \t Current Round: \n {self.current_round}"
            print(s)

    def is_next_round(self):
        if self.active_players == []:
            print("No active players")
            return False
        can_continue = self.round_index < len(GAME_ROUNDS) - 1
        return can_continue and self.current_round.is_round_complete()
    
    def is_game_over(self):
        if self.active_players == [] and self.players != []:
            if self.is_running:
                self.is_running = False
            return not self.is_running

        if self.round_index >= len(GAME_ROUNDS):
            print("This can't happen")
            return False

        return not self.is_running
    
    def get_current_round(self):
        return GAME_ROUNDS[self.round_index]
    
    def get_current_waiting_for(self):
        return self.current_round.get_current_player()
    
    def get_player_hands(self, player_id: int) -> List[str]:
        return [str(card) for card in self.hands[player_id]]

    def is_current_round_complete(self):

        return self.current_round.is_round_complete()

    def start_game(self):
        self.game_start_time = int(time.time() * 1000)
        self.deck = PokerDeck()
        self.deck.shuffle()
        self.round_index = 0
        self.is_running = True
        self.blind_players_added_back = False  # Reset for new game

        # Use shared simulation game ID if provided, otherwise generate new one
        game_id = self.simulation_game_id if self.simulation_game_id else str(uuid.uuid4())
        
        self.json_game_log = {
            "gameId": game_id,
            "rounds": {},
            "playerNames": {},
            "blinds": {},
            "finalBoard": [],
            "sidePots": []
        }
        
        # Add player money information if available
        if self.player_starting_money or self.player_delta:
            self.json_game_log["playerMoney"] = {
                "initialAmount": self.initial_money,
                "startingMoney": {str(p_id): money for p_id, money in self.player_starting_money.items()},
                "startingDelta": {str(p_id): delta for p_id, delta in self.player_delta.items()}
            }

        # Deal two cards to each player
        for player in self.active_players:
            self.hands[player] = self.deck.deal(2)

        
        self.total_pot = 0
        self.historical_pots = []
        self.player_history = {}
        self.score = {
            player: 0 for player in self.active_players
        }
        
        # Blinds are now assigned by the server before calling start_game()
        # self.assign_blinds()  # Removed - handled by server
        
        self.json_game_log['playerNames'] = {p_id - 1: f"player{p_id}" for p_id in self.players}

        self.json_game_log['playerHands'] = {p_id - 1: [str(card) for card in hand] for p_id, hand in self.hands.items()}

        self.json_game_log['blinds'] = {
            "small": self.blind_amount // 2,
            "big": self.blind_amount
        }

        # Initialize the first round
        self.current_round = RoundState(self.active_players)
        
        # Don't post blinds automatically - let clients handle it when they receive action requests

    def post_blinds(self):
        if not self.small_blind_player or not self.big_blind_player:
            print("No small or big blind player")
            return
        
        # Post forced blinds using the special method that doesn't affect waiting_for
        self.current_round.post_forced_blind(
            self.small_blind_player, 
            PokerAction.RAISE, 
            self.blind_amount // 2
        )
        self.current_round.post_forced_blind(
            self.big_blind_player, 
            PokerAction.RAISE, 
            self.blind_amount
        )
        
        # Remove blind players from waiting_for since they've posted forced bets
        # They will be added back later in the correct order after other players act
        self.current_round.waiting_for.discard(self.small_blind_player)
        self.current_round.waiting_for.discard(self.big_blind_player)

    def update_game(self, player_id: int, action: Tuple[PokerAction, int]):
        if player_id not in self.active_players:
            raise ValueError("Player is not active in the game")
        
        action_type, amount = action
        # All in propagation
        if self.round_index > 1:
            if self.player_history[self.round_index - 1]["player_actions"][player_id] == PokerAction.ALL_IN:
                if self.debug:
                    print(f"Player {player_id} is all in from previous round")
                action_type, amount = PokerAction.ALL_IN, 0

        # Calculate cumulative pot information from all previous rounds
        cumulative_pot = 0
        cumulative_side_pots = []
        side_pot_id_counter = 0
        
        # Add historical pots from completed rounds
        for round_idx in self.player_history:
            round_history = self.player_history[round_idx]
            # Add the total pot amount for this round (just once per round)
            cumulative_pot += round_history["pot"]
            
            # For side pots, use the final state of the round if available
            if "action_sequence" in round_history and round_history["action_sequence"]:
                final_action = round_history["action_sequence"][-1]
                # Add side pots with unique IDs from the final action of the round
                for side_pot in final_action["side_pots_after_action"]:
                    cumulative_side_pots.append({
                        "id": side_pot_id_counter,
                        "amount": side_pot["amount"],
                        "eligible_players": side_pot["eligible_players"]
                    })
                    side_pot_id_counter += 1

        # Update round state with cumulative information
        self.current_round.set_cumulative_pot_info(cumulative_pot, cumulative_side_pots)
        
        # Update round state
        self.current_round.update_player_action(player_id, action_type, amount)

        relative_time = int(time.time() * 1000) - self.game_start_time
        self.current_round.player_action_times[player_id] = relative_time
        
        # Remove player from active players if they folded
        if action_type == PokerAction.FOLD:
            self.active_players.remove(player_id)
            
        # Special preflop logic: After all non-blind players have acted once, 
        # add blind players back for their option to act
        if self.round_index == 0:  # Preflop only
            self._check_and_add_blind_players_back()

    def _check_and_add_blind_players_back(self):
        """Check if all non-blind players have acted and add blind players back if so"""
        if not self.small_blind_player or not self.big_blind_player:
            return
            
        # Get all original non-blind players (including those who may have folded)
        # We need to check against the initial active players, not current ones
        all_original_players = [p for p in self.current_round.player_bets.keys()]
        non_blind_players = [p for p in all_original_players 
                           if p != self.small_blind_player and p != self.big_blind_player]
        
        # Check if all non-blind players have acted (have an action recorded)
        all_non_blind_acted = all(
            p in self.current_round.player_actions and 
            self.current_round.player_actions[p] is not None 
            for p in non_blind_players
        )
        
        # Check if blind players are not currently waiting (meaning they haven't been added back yet)
        blind_players_not_waiting = (
            self.small_blind_player not in self.current_round.waiting_for and
            self.big_blind_player not in self.current_round.waiting_for
        )
        
        # If all non-blind players have acted and blind players aren't waiting and haven't been added back yet
        if (all_non_blind_acted and blind_players_not_waiting and 
            len(non_blind_players) > 0 and not self.blind_players_added_back):
            if self.debug:
                print(f"All non-blind players have acted. Adding blind players back for their option.")
            self.current_round.add_blind_players_for_second_action(
                self.small_blind_player, 
                self.big_blind_player
            )
            self.blind_players_added_back = True  # Mark that we've added them back

    def start_round(self):
        if not self.is_next_round():
            self.end_game()
            return

        self.round_index += 1
        
        # Create new round state
        self.current_round = RoundState(self.active_players)

        if(GAME_ROUNDS[self.round_index] == PokerRound.FLOP):
            # Burn one card
            self.deck.deal(1)
            # Deal the flop
            self.board = self.deck.deal(3)
        else:
            self.deck.deal(1)  # Burn a card
            new_card = self.deck.deal(1)[0]  # Deal one new board card
            self.board.append(new_card)

        self.json_game_log['finalBoard'] = [str(card) for card in self.board]
        

    def end_round(self):
        if not self.current_round.is_round_complete():
            raise ValueError("Round cannot end while players are still waiting to act")
        
        # Convert action history to the new format
        action_sequence = []
        for action_record in self.current_round.action_history:
            action_sequence.append({
                "player": action_record.player_id - 1,  # Convert to 0-based indexing for JSON
                "action": get_poker_action_name_from_enum(action_record.action).upper(),
                "amount": action_record.amount,
                "timestamp": action_record.timestamp,
                # Round-specific pot information
                "pot_after_action": action_record.pot_after_action,
                "side_pots_after_action": action_record.side_pots_after_action,
                # Cumulative pot information across all rounds
                "total_pot_after_action": action_record.total_pot_after_action,
                "total_side_pots_after_action": action_record.total_side_pots_after_action
            })

        # Keep backward compatibility with old format for now
        actions = {
            p_id - 1: get_poker_action_name_from_enum(action).upper() if action else "NO_ACTION"
            for p_id, action in self.current_round.player_actions.items()
        }

        self.json_game_log['rounds'][self.round_index] = {
            "pot": self.current_round.pot,
            "bets": {p_id - 1: bet for p_id, bet in self.current_round.player_bets.items()},
            "actions": actions,  # Keep old format for backward compatibility
            "action_sequence": action_sequence,  # New detailed action sequence
            "actionTimes": {p_id - 1: t for p_id, t in self.current_round.player_action_times.items()}
        }

        self.historical_pots.append(self.current_round.pot)
        self.total_pot += self.current_round.pot
        self.player_history[self.round_index] =  {
            "pot": self.current_round.pot,
            "player_bets": self.current_round.player_bets,
            "player_actions": self.current_round.player_actions,
            "action_sequence": action_sequence  # Store new format in history too
        }

    def end_game(self):
        # Ensure current round bets are included in player history if not already
        if self.current_round and self.round_index not in self.player_history:
            self.player_history[self.round_index] = {
                "pot": self.current_round.pot,
                "player_bets": self.current_round.player_bets,
                "player_actions": self.current_round.player_actions
            }
        
        # Calculate total pot from all rounds - this is the most reliable approach
        total_pot_amount = 0
        for round_index in self.player_history:
            round_bets = self.player_history[round_index]["player_bets"]
            total_pot_amount += sum(round_bets.values())
        
        if self.debug:
            print(f"Total pot amount calculated from all rounds: {total_pot_amount}")
        
        # Calculate cumulative side pots that respect all-in limits
        final_pots = self._calculate_cumulative_side_pots()
        
        # Initialize all player scores to 0
        for player in self.players:
            self.score[player] = 0
        
        # Check if all players folded except one - this player should win the pot
        if self.current_round:
            if self.round_index == 0:
                print("this get called")
                non_folded_players = [player_id for player_id in self.active_players]
            else:
                print("this get called 2")
                if len(self.active_players) < 0:
                    non_folded_players = [
                        player_id for player_id in self.player_history[self.round_index]["player_actions"]
                        if self.player_history[self.round_index]["player_actions"][player_id] != PokerAction.FOLD
                    ]
                else:
                    non_folded_players = self.active_players

                print("round index: ", self.round_index)
                print("player history: ", self.player_history)
                print("Active players: ", self.active_players)

            # if all players folded, the last player who acted is the winner
            if len(non_folded_players) == 0:
                print("Everyone folded, default to last player who acted")
                last_folded_player = self.player_history[max(self.round_index - 1, 0)]["action_sequence"][-1]["player"]
                non_folded_players.append(int(last_folded_player) + 1)
                # winner = self.current_round.player_actions[self.current_round.bettor]
                # self.score[winner] = total_pot_amount
                # return

            print(f"Non folded players: {non_folded_players}")
            
            if len(non_folded_players) == 1:
                print(f"All players folded except {non_folded_players[0]}. Awarding entire pot of {total_pot_amount} to {non_folded_players[0]}")
                # Only one player didn't fold - they win the entire pot
                winner = non_folded_players[0]
                self.score[winner] = total_pot_amount
                
                if self.debug:
                    print(f"All players folded except {winner}. Awarding entire pot of {total_pot_amount} to {winner}")
                
                # Subtract each player's total bets from their score
                for player in self.players:
                    total_bets = 0
                    for round_index in self.player_history:
                        if player in self.player_history[round_index]["player_bets"]:
                            total_bets += self.player_history[round_index]["player_bets"][player]
                    self.score[player] -= total_bets
                
                if self.debug:
                    print(f"Final Scores: {self.score}")
                    total_score = sum(self.score.values())
                    print(f"Total score (should be 0): {total_score}")
                
                self.is_running = False
                
                # Handle JSON logging for this case
                if self.current_round and hasattr(self.current_round, 'get_side_pots_info'):
                    side_pots_info = self.current_round.get_side_pots_info()
                    self.json_game_log['sidePots'] = [
                        {
                            "amount": pot["amount"],
                            "eligible_players": [p - 1 for p in pot["eligible_players"]]
                        }
                        for pot in side_pots_info
                    ]
                
                # Add final money and delta information to the game log
                if 'playerMoney' not in self.json_game_log:
                    self.json_game_log['playerMoney'] = {}
                
                
                # Calculate final delta as starting delta + current game delta
                final_deltas = {}
                for player_id in self.score:
                    starting_delta = self.player_delta.get(player_id, 0)
                    current_game_delta = self.score[player_id]
                    final_deltas[str(player_id)] = starting_delta + current_game_delta
                
                self.json_game_log['playerMoney']['finalDelta'] = final_deltas
                self.json_game_log['playerMoney']['gameScores'] = {str(p_id): score for p_id, score in self.score.items()}
                self.json_game_log['playerMoney']['finalMoney'] = {str(p_id): money + self.score[p_id] for p_id, money in self.player_final_money.items()}
                
                # Calculate game deltas (difference between final and starting money)
                game_deltas = {}
                for player_id in self.score:
                    game_deltas[str(player_id)] = self.score[player_id]
                
                self.json_game_log['playerMoney']['thisGameDelta'] = game_deltas
                
                # Write game log to file
                self._write_game_log_to_file()
                return
        
        # Evaluate hands for all active players
        hand_values = {}
        for player in self.active_players:
            players_hand = self.hands[player].copy()
            players_hand.extend(self.board)
            hand_values[player] = eval7.evaluate(players_hand)
        
        if self.debug:
            print(f"Hand values: {hand_values}")
            print(f"Distributing {len(final_pots)} pot(s)")
        
        # Award each pot to the best hand among eligible players
        for i, pot in enumerate(final_pots):
            print(f"Pot {i}: {pot.amount} chips, eligible players: {pot.eligible_players}")
            print(f"Active players: {self.active_players}")
            print(f"Player history: {self.player_history}")
            if pot.amount == 0:
                continue
                
            # Find eligible players who are still active
            eligible_active_players = pot.eligible_players.intersection(set(self.active_players))
            
            if len(eligible_active_players) == 0:
                if self.debug:
                    print(f"Pot {i}: No eligible active players, pot amount {pot.amount} is lost")
                continue
            
            # Find the best hand among eligible players
            eligible_hand_values = {player: hand_values[player] for player in eligible_active_players}
            pot_winners = [player for player, value in eligible_hand_values.items() 
                          if value == max(eligible_hand_values.values())]
            
            # Split pot among tied winners
            pot_share = pot.amount // len(pot_winners)
            remainder = pot.amount % len(pot_winners)
            
            if self.debug:
                print(f"Pot {i}: {pot.amount} chips, eligible players: {eligible_active_players}")
                print(f"Winners: {pot_winners}, each gets {pot_share} chips")
                if remainder > 0:
                    print(f"Remainder of {remainder} chips goes to player {pot_winners[0]}")
            
            for j, winner in enumerate(pot_winners):
                self.score[winner] += pot_share
                # Give remainder to first winner (arbitrary but fair)
                if j == 0:
                    self.score[winner] += remainder

        if self.debug:
            print(f"Player hands:")
            for player in self.active_players:
                print(f"  Player {player}: {self.hands[player]}")
            print(f"Total pot distributed: {sum(pot.amount for pot in final_pots)}")

        # Subtract each player's total bets from their score
        for player in self.players:
            total_bets = 0
            for round_index in self.player_history:
                if player in self.player_history[round_index]["player_bets"]:
                    total_bets += self.player_history[round_index]["player_bets"][player]
            self.score[player] -= total_bets
            
            if self.debug:
                print(f"Player {player}: total bets = {total_bets}, final score = {self.score[player]}")

        if True:
            print(f"Final Scores: {self.score}")
            # Verify zero-sum
            total_score = sum(self.score.values())
            print(f"Total score (should be 0): {total_score}")

        self.is_running = False
        # Blind rotation is now handled by the server

        if self.current_round and hasattr(self.current_round, 'get_side_pots_info'):
            side_pots_info = self.current_round.get_side_pots_info()
            self.json_game_log['sidePots'] = [
                {
                    "amount": pot["amount"],
                    "eligible_players": [p - 1 for p in pot["eligible_players"]]
                }
                for pot in side_pots_info
            ]

        # Add final money and delta information to the game log
        if 'playerMoney' not in self.json_game_log:
            self.json_game_log['playerMoney'] = {}
        
        
        # Calculate final delta as starting delta + current game delta
        final_deltas = {}
        for player_id in self.score:
            starting_delta = self.player_delta.get(player_id, 0)
            current_game_delta = self.score[player_id]
            final_deltas[str(player_id)] = starting_delta + current_game_delta
        
        self.json_game_log['playerMoney']['finalDelta'] = final_deltas
        self.json_game_log['playerMoney']['gameScores'] = {str(p_id): score for p_id, score in self.score.items()}
        self.json_game_log['playerMoney']['finalMoney'] = {str(p_id): money + self.score[p_id] for p_id, money in self.player_final_money.items()}
        
        # Calculate game deltas (difference between final and starting money)
        game_deltas = {}
        for player_id in self.score:
            game_deltas[str(player_id)] = self.score[player_id]
        
        self.json_game_log['playerMoney']['thisGameDelta'] = game_deltas
        
        # Write game log to file
        self._write_game_log_to_file()

    def _calculate_cumulative_side_pots(self):
        """Calculate cumulative side pots that respect all-in limits from the first round"""
        # Get all active players (not folded)
        active_players = set()
        for player_id, action in self.current_round.player_actions.items():
            if action != PokerAction.FOLD:
                active_players.add(player_id)
        
        if len(active_players) <= 1:
            # Single active player or none
            total_pot = sum(sum(round_bets.values()) for round_bets in 
                           [self.player_history[round_idx]["player_bets"] for round_idx in self.player_history])
            if len(active_players) == 1:
                return [type('Pot', (), {'amount': total_pot, 'eligible_players': active_players})()]
            else:
                return [type('Pot', (), {'amount': total_pot, 'eligible_players': set()})()]
        
        # Calculate cumulative bet amounts for each player
        cumulative_bets = {}
        for player in self.players:
            cumulative_bets[player] = 0
            for round_index in self.player_history:
                if player in self.player_history[round_index]["player_bets"]:
                    cumulative_bets[player] += self.player_history[round_index]["player_bets"][player]
        
        # Get unique bet levels in ascending order
        bet_levels = sorted(set(bet for bet in cumulative_bets.values() if bet > 0))
        
        if len(bet_levels) <= 1:
            # All players bet the same amount
            total_pot = sum(cumulative_bets.values())
            return [type('Pot', (), {'amount': total_pot, 'eligible_players': active_players})()]
        
        # Create side pots for each betting level
        pots = []
        for i, current_level in enumerate(bet_levels):
            prev_level = bet_levels[i-1] if i > 0 else 0
            level_contribution = current_level - prev_level
            
            # Find players who contributed to this level
            eligible_players = set()
            contributing_count = 0
            for player_id, bet_amount in cumulative_bets.items():
                if bet_amount >= current_level:
                    contributing_count += 1
                    # Only active players are eligible to win
                    if player_id in active_players:
                        # CRITICAL FIX: All-in players from previous rounds should only be eligible
                        # for pots up to their all-in amount, not for pots created by subsequent betting
                        if player_id in self.current_round.all_in_players:
                            # Check if this player went all-in in a previous round
                            # and if so, only include them if this pot level doesn't exceed their all-in amount
                            all_in_amount = cumulative_bets[player_id]
                            if current_level <= all_in_amount:
                                eligible_players.add(player_id)
                        else:
                            # Non-all-in players are eligible for all pots
                            eligible_players.add(player_id)
            
            if contributing_count > 0 and level_contribution > 0:
                pot_amount = level_contribution * contributing_count
                pots.append(type('Pot', (), {'amount': pot_amount, 'eligible_players': eligible_players})())
        
        # If no pots were created, create a single main pot
        if len(pots) == 0:
            total_pot = sum(cumulative_bets.values())
            pots = [type('Pot', (), {'amount': total_pot, 'eligible_players': active_players})()]
        
        return pots

    def _write_game_log_to_file(self):
        """Write the game log to a JSON file"""
        try:
            game_id = self.json_game_log.get('gameId', f"unknown_{int(time.time())}")
            
            # Include game sequence number in filename if available
            if self.game_sequence is not None:
                filename = f"game_log_{self.game_sequence}_{game_id}.json"
            else:
                filename = f"game_log_{game_id}.json"
                
            os.makedirs(BASE_PATH, exist_ok=True)
            filepath = os.path.join(BASE_PATH, filename)

            with open(filepath, 'w') as f:
                json.dump(self.json_game_log, f, indent = 2)

            if self.debug:
                print(f"Game log successfully written to {filepath}")
        except Exception as e:
            print(f"Error writing game log to JSON: {e}")

    def get_final_score(self):
        return self.score
    
    def get_game_state(self, player_money: Dict[int, int] = None) -> GameStateMessage:
        round_name = get_round_name(self.round_index)
        actions_text = {}
        for player in self.current_round.player_actions:
            if self.current_round.player_actions[player] == None:
                continue
            actions_text[player] = get_poker_action_name_from_enum(self.current_round.player_actions[player])

        # Get side pot information
        side_pots_info = self.current_round.get_side_pots_info() if hasattr(self.current_round, 'get_side_pots_info') else []

        return GameStateMessage(
            round_num=self.round_index,
            round=round_name,
            community_cards=self.board,
            pot=self.current_round.pot,
            current_player=self.current_round.get_current_player(),
            current_bet=self.current_round.raise_amount,
            player_bets=self.current_round.player_bets,
            player_actions=actions_text,
            player_money=player_money,
            min_raise=self.current_round.raise_amount,
            max_raise=self.current_round.raise_amount * 2,
            side_pots=side_pots_info
        )

    def get_positional_order(self, players_to_order: List[int]) -> List[int]:
        """
        Get players in positional order for post-flop betting rounds.
        Action starts with the first active player to the left of the dealer button.
        """
        if not players_to_order:
            return []
        
        # For post-flop rounds, find the first active player to the left of the dealer button
        # In multi-player games, this is typically the small blind position
        # In heads-up, this is the big blind position
        
        # Get all players in their seated order
        all_players = self.players.copy()
        num_players = len(all_players)
        
        if num_players < 2:
            return players_to_order
        
        # Find the starting position for post-flop action
        if num_players == 2:
            # Heads-up: small blind acts first post-flop
            start_pos = (self.dealer_button_position) % num_players
        else:
            # Multi-player: small blind acts first post-flop (to the left of dealer)
            start_pos = (self.dealer_button_position) % num_players
        
        # Create ordered list starting from the correct position
        ordered_players = []
        for i in range(num_players):
            player_pos = (start_pos + i) % num_players
            player_id = all_players[player_pos]
            if player_id in players_to_order:
                ordered_players.append(player_id)
        
        return ordered_players

    def get_preflop_order(self, players_to_order: List[int]) -> List[int]:
        """
        Get players in order for preflop betting.
        Pre-flop order: Small blind acts first, then continue clockwise,
        with big blind acting last.
        """
        if not players_to_order:
            return []
        
        # Get all players in their seated order
        all_players = self.players.copy()
        num_players = len(all_players)
        
        if num_players < 2:
            return players_to_order
        
        # Find the starting position for pre-flop action (small blind position)
        if num_players == 2:
            # Heads-up: small blind (dealer) acts first pre-flop
            start_pos = self.dealer_button_position % num_players
        else:
            # Multi-player: small blind acts first pre-flop
            # Small blind is at position (dealer_button_position + 1) % num_players
            start_pos = (self.dealer_button_position + 2) % num_players
        
        # Create ordered list starting from small blind position
        ordered_players = []
        for i in range(num_players):
            player_pos = (start_pos + i) % num_players
            player_id = all_players[player_pos]
            if player_id in players_to_order:
                ordered_players.append(player_id)
        
        return ordered_players

    def set_player_money_info(self, player_starting_money: Dict[int, int], player_delta: Dict[int, int], initial_money: int):
        """Set player money information from the server"""
        self.player_starting_money = player_starting_money.copy()
        self.player_delta = player_delta.copy()
        self.initial_money = initial_money
        
        # Calculate final money for each player
        for player_id in self.players:
            if player_id in player_starting_money:
                self.player_final_money[player_id] = player_starting_money[player_id]

    def update_final_money_after_game(self, game_scores: Dict[int, int], updated_player_money: Dict[int, int], updated_player_delta: Dict[int, int]):
        """Update final money and delta information after game ends"""
        self.player_delta = updated_player_delta.copy()