import socket
import threading
import time
from typing import Dict, Tuple
import uuid
import logging
from config import (
    HOST,
    PORT,
    OUTPUT_GAME_RESULT_FILE, 
    OUTPUT_FILE_SIMULATION,
    RETRY_COUNT,
    SERVER_SIM_WAIT_BETWEEN_GAMES, 
    DEFAULT_NUM_PLAYERS, 
    DEFAULT_TURN_TIMEOUT, 
    DEFAULT_BLIND_AMOUNT, 
    DEFAULT_BLIND_MULTIPLIER, 
    DEFAULT_BLIND_INCREASE_INTERVAL, 
    DEFAULT_INITIAL_MONEY
)
from game.game import Game
import os

from message import (
    CONNECT,
    END, 
    GAME_STATE,
    PLAYER_ACTION, 
    REQUEST_PLAYER_MESSAGE, 
    ROUND_END, 
    ROUND_START, 
    START, TEXT, 
    Message
)

from poker_type.game import PokerAction
from poker_type.utils import (
    get_poker_action_enum_from_index, 
    get_round_name, 
    get_round_name_from_enum
)

logger = logging.getLogger(__name__)

class PokerEngineServer:
    def __init__(self, 
                 host: str = HOST, 
                 port: int = PORT, 
                 num_players: int = DEFAULT_NUM_PLAYERS,
                 turn_timeout: int = DEFAULT_TURN_TIMEOUT, 
                 debug: bool = False, 
                 sim: bool = False, 
                 blind_amount: int = DEFAULT_BLIND_AMOUNT, 
                 blind_multiplier: float = DEFAULT_BLIND_MULTIPLIER, 
                 blind_increase_interval: int = DEFAULT_BLIND_INCREASE_INTERVAL, 
                 initial_money: int = DEFAULT_INITIAL_MONEY):
        self.host = host
        self.port = port
        self.required_players = num_players
        self.turn_timeout = turn_timeout
        self.debug = debug
        self.sim = sim
        self.blind_amount = blind_amount
        self.initial_blind_amount = blind_amount  # Store the initial blind amount
        self.blind_multiplier = blind_multiplier
        self.blind_increase_interval = blind_increase_interval
        self.initial_money = initial_money  # Initial money for each player
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Generate one game ID for the entire simulation sequence
        self.simulation_game_id = str(uuid.uuid4()) if self.sim else None
        
        self.game = Game(self.debug, self.blind_amount, 0, self.simulation_game_id)  # Initial game with sequence 0
        self.player_connections: Dict[int, socket.socket] = {}
        self.player_addresses: Dict[int, Tuple[str, int]] = {}
        self.player_money: Dict[int, int] = {}  # Track player money between games
        self.player_delta: Dict[int, int] = {}  # Track cumulative delta (change from initial money)
        self.game_in_progress = False
        self.server_lock = threading.Lock()
        self.game_lock = threading.Lock()
        self.running = True
        self.current_player_idx = 0
        self.game_count = 0
        
        # Dealer button management for continuous games
        self.dealer_button_position = 0

    def start_server(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.required_players)
            logger.info(f"Server started on {self.host}:{self.port}")
            print(f"Server started on {self.host}:{self.port}")
            logger.info(f"Waiting for {self.required_players} players to join...")
            print(f"Waiting for {self.required_players} players to join...")
            if not self.sim:
                self.remove_file_content(OUTPUT_GAME_RESULT_FILE)
                self.append_to_file(OUTPUT_GAME_RESULT_FILE, "RUNNING")
            self.accept_connections()
        except Exception as e:
            logger.error(f"Error starting server: {e.with_traceback()}")
            print(f"Error starting server: {e}")
            self.stop_server()

    def stop_server(self):
        self.running = False
        self.server_socket.close()
        for conn in self.player_connections.values():
            conn.close()
        
        # If this was a simulation, replace RUNNING with DONE
        if self.sim:
            self.replace_running_with_done()
        
        logger.info("Server stopped.")
        print("Server stopped.")

    def replace_running_with_done(self):
        """Replace RUNNING with DONE in the simulation output file"""
        try:
            if os.path.exists(OUTPUT_FILE_SIMULATION):
                with open(OUTPUT_FILE_SIMULATION, 'r') as file:
                    content = file.read()
                
                # Replace RUNNING with DONE
                content = content.replace("RUNNING", "DONE")
                
                with open(OUTPUT_FILE_SIMULATION, 'w') as file:
                    file.write(content)
                
                logger.info("Simulation status updated to DONE")
                print("Simulation status updated to DONE")
        except Exception as e:
            logger.error(f"Error updating simulation status: {e}")
            print(f"Error updating simulation status: {e}")

    def accept_connections(self):
        while self.running and len(self.player_connections) < self.required_players:
            try:
                client_socket, address = self.server_socket.accept()
                player_id = self.generate_player_id()
                self.player_connections[player_id] = client_socket
                self.player_addresses[player_id] = address
                
                # Initialize player money and delta for new connections
                if player_id not in self.player_money:
                    self.player_money[player_id] = self.initial_money
                    self.player_delta[player_id] = 0  # Start with 0 delta
                
                logger.info(f"Player {player_id} connected from {address} with {self.player_money[player_id]} money (delta: {self.player_delta[player_id]})")
                print(f"Player {player_id} connected from {address} with {self.player_money[player_id]} money (delta: {self.player_delta[player_id]})")

                with self.game_lock:
                    self.game.add_player(player_id)
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
                    print(f"Error accepting connection: {e}")
                break

        if len(self.player_connections) == self.required_players:
            self.run_continuous_games()

    def update_blind_amount(self):
        """Update blind amount based on the game count and blind increase settings"""
        if self.blind_increase_interval > 0 and self.game_count > 0:
            # Calculate how many times the blind should have increased
            increase_count = self.game_count // self.blind_increase_interval
            if increase_count > 0:
                # Calculate new blind amount
                new_blind_amount = int(self.initial_blind_amount * (self.blind_multiplier ** increase_count))
                if new_blind_amount != self.blind_amount:
                    old_blind = self.blind_amount
                    self.blind_amount = new_blind_amount
                    print(f"Blind increased from {old_blind} to {self.blind_amount} (increase #{increase_count})")
                    self.broadcast_text(f"Blind amount increased to {self.blind_amount}!")

    def reset_game_state(self):
        """Reset the game state for a new game while keeping the same players"""
        with self.game_lock:
            # Update blind amount if needed
            self.update_blind_amount()
            
            # Create a new game instance with the current blind amount, game sequence, and shared game ID
            self.game = Game(self.debug, self.blind_amount, self.game_count, self.simulation_game_id)
            
            # Set the current dealer button position
            self.game.set_dealer_button_position(self.dealer_button_position)
            
            # Add all existing players to the new game
            for player_id in self.player_connections.keys():
                self.game.add_player(player_id)
            
            # Pass player money information to the game
            self.game.set_player_money_info(
                self.player_money.copy(),
                self.player_delta.copy(),
                self.initial_money
            )
            
            self.game_in_progress = False
            self.current_player_idx = 0

    def run_continuous_games(self):
        """Run multiple games with the same connections"""
        while self.running and len(self.player_connections) >= self.required_players:
            self.game_count += 1
            logger.info(f"=== Starting Game #{self.game_count} ===")
            print(f"\n=== Starting Game #{self.game_count} ===")
            logger.info(f"Dealer button position: {self.dealer_button_position}")
            print(f"Dealer button position: {self.dealer_button_position}")
            
            # Check if we've reached the simulation rounds limit
            if hasattr(self, 'simulation_rounds') and self.game_count > self.simulation_rounds:
                logger.info(f"Reached simulation limit of {self.simulation_rounds} games. Stopping.")
                print(f"Reached simulation limit of {self.simulation_rounds} games. Stopping.")
                break
            
            # Reset game state for new game
            self.reset_game_state()
            
            # Run a single game
            self.run_single_game()
            
            # Rotate dealer button after each game for continuous mode
            self.rotate_dealer_button()
            
            # Check if we should continue
            if len(self.player_connections) < self.required_players:
                logger.warning("Not enough players remaining, stopping server.")
                print("Not enough players remaining, stopping server.")
                break
            
            # Wait a bit before starting the next game
            logger.info(f"Waiting {SERVER_SIM_WAIT_BETWEEN_GAMES} seconds before starting next game...")
            print(f"Waiting {SERVER_SIM_WAIT_BETWEEN_GAMES} seconds before starting next game...")
            time.sleep(SERVER_SIM_WAIT_BETWEEN_GAMES)
        
        logger.info("Game session ended.")
        print("Game session ended.")
        self.stop_server()

    def run_single_game(self):
        """Run a single game"""
        with self.game_lock:
            self.game_in_progress = True
        
        self.broadcast_text(f"Game #{self.game_count} starting!")

        for(player_id, conn) in self.player_connections.items():
            connect_message = CONNECT(player_id)
            self.send_message(player_id, str(connect_message))
            self.send_text_message(player_id, f"Welcome to Game #{self.game_count}! Your ID is {player_id}")

        # Assign blinds with money check - this will handle players who can't afford blinds
        forced_fold_players = self.game.assign_blinds_with_money_check(self.player_money, self.blind_amount)
        
        # Handle players who were forced to fold due to insufficient money
        for player_id in forced_fold_players:
            logger.warning(f"Player {player_id} forced to fold due to insufficient money for blinds")
            print(f"Player {player_id} forced to fold due to insufficient money for blinds")
            self.broadcast_text(f"Player {player_id} automatically folded due to insufficient money for blinds")
        
        # Start the game after blind assignment
        self.game.start_game()
        
        # broadcast message with hands to each player
        all_player_ids = list(self.player_connections.keys())
        for (player_id, conn) in self.player_connections.items():
            if player_id in forced_fold_players:
                continue
            # logger.debug(f"Player {player_id} hands: {self.game.get_player_hands(player_id)}")
            
            # Determine if this player is small blind or big blind
            is_small_blind = player_id == self.game.get_small_blind_player()
            is_big_blind = player_id == self.game.get_big_blind_player()
            logger.info(f"Player {player_id} is small blind: {is_small_blind}, big blind: {is_big_blind}")
            
            start_message = START(
                "Game initiated!", 
                self.game.get_player_hands(player_id),
                self.blind_amount,
                is_small_blind,
                is_big_blind,
                self.game.get_small_blind_player(),
                self.game.get_big_blind_player(),
                all_player_ids
            )
            logger.debug(f"Sending start message to player {player_id}: {str(start_message)}")  
            self.send_message(player_id, str(start_message))
        
        self.game.post_blinds()
        self.broadcast_game_state()

        round_start_message = ROUND_START(get_round_name_from_enum(self.game.get_current_round()))
        self.current_player_idx = 0
        self.broadcast_message(round_start_message)

        waiting_for = self.game.get_current_waiting_for()

        try:
            while self.running and self.game_in_progress:
                # new game with one player left -> end game
                # round complete and game over -> end game
                if len(self.game.active_players) == 1 or (self.game.is_current_round_complete() and self.game.is_game_over()):
                    self.broadcast_text(f"Game #{self.game_count} over!")
                    
                    # CRITICAL: Call end_game() to calculate scores and write logs
                    if self.game.is_running:
                        logger.info("Calling end_game() for proper scoring and logging")
                        print("Calling end_game() for proper scoring and logging")
                        self.game.end_game()
                    
                    score = self.game.get_final_score()
                    logger.info(f"Final score: {score}")
                    
                    # Update player money based on game results
                    self.update_player_money_after_game(score)
                    
                    # Update the game with final money information for logging
                    self.game.update_final_money_after_game(score, self.player_money.copy(), self.player_delta.copy())
                    
                    for player_id in score.keys():
                        # get active players hands information
                        active_players = self.game.get_active_players()
                        active_players_hands = {player_id: self.game.get_player_hands(player_id) for player_id in active_players}
                        end_message = END(score[player_id], score, active_players_hands)
                        print(f"End message: {end_message}")
                        print(f"Score: {score}")
                        self.send_message(player_id, str(end_message))
                    # TODO: Add a reveal cards message
                    self.game_in_progress = False

                    if not self.sim:
                        self.append_to_file(OUTPUT_GAME_RESULT_FILE, f"GAME_{self.game_count} " + str(score))
                    else:
                        pass
                    break

                self.broadcast_text("New round starting!")
                self.broadcast_game_state()
                
                # round logic
                while not self.game.is_current_round_complete():
                    waiting_for = self.game.get_current_waiting_for()
                    length = len(waiting_for)
                    if length == 0:
                        break

                    logger.debug(f"Current player in game: {waiting_for}")
                    
                    # Get players in proper positional order
                    players_list = list(waiting_for)
                    if self.game.round_index == 0:
                        # Preflop: small blind first, then big blind, then others
                        queue = self.game.get_preflop_order(players_list)
                    else:
                        # Post-flop: positional order starting from small blind position
                        queue = self.game.get_positional_order(players_list)
                    
                    logger.debug(f"Action order: {queue}")
                    print(f"Action order: {queue}")
                    
                    start_player_idx = 0
                    length = len(queue)

                    idx = start_player_idx
                    while idx < start_player_idx + length:
                        logger.debug(f"Current player index: {idx}, Player ID: {queue[idx % length]}")
                        print(f"Current player index: {idx}, Player ID: {queue[idx % length]}")
                        player_id = queue[idx % length]
                        
                        if player_id not in self.player_connections:
                            idx += 1
                            continue  # Skip removed players
                        
                        retry_count = 0
                        action_processed = False
                        
                        while retry_count < RETRY_COUNT and not action_processed:
                            conn = self.player_connections[player_id]
                            
                            # Check if player is still connected
                            if player_id not in self.player_connections:
                                break

                            request_action_message = REQUEST_PLAYER_MESSAGE(player_id, 0)
                            self.send_message(player_id, str(request_action_message))

                            try:
                                conn.settimeout(5)
                                action = conn.recv(4096).decode('utf-8')
                                
                                if not action:
                                    retry_count += 1
                                    self.send_text_message(player_id, f"Invalid action. Try again. ({retry_count}/{RETRY_COUNT})")
                                    logger.info(f"Player {player_id} sent empty action. Retry {retry_count}/{RETRY_COUNT}")
                                    continue

                                action = action.strip()
                                if action == "":
                                    retry_count += 1
                                    self.send_text_message(player_id, f"Invalid action. Try again. ({retry_count}/{RETRY_COUNT})")
                                    logger.info(f"Player {player_id} sent empty action. Retry {retry_count}/{RETRY_COUNT}")
                                    continue
                                
                                logger.info(f"Player {player_id} action: {action}")
                                print(f"Player {player_id} action: {action}")
                                
                                ok = self.process_action(player_id, action)
                                if ok:
                                    action_processed = True
                                    logger.info(f"Player {player_id} action processed successfully")
                                else:
                                    retry_count += 1
                                    self.send_text_message(player_id, f"Invalid action. Try again. ({retry_count}/{RETRY_COUNT})")
                                    logger.info(f"Player {player_id} sent invalid action. Retry {retry_count}/{RETRY_COUNT}")
                                    
                            except socket.timeout:
                                retry_count += 1
                                logger.warning(f"Player {player_id} timeout. Retry {retry_count}/{RETRY_COUNT}")
                                self.send_text_message(player_id, f"Timeout! Try again. ({retry_count}/{RETRY_COUNT})")
                                
                            except Exception as e:
                                logger.error(f"Error receiving action from player {player_id}: {e}")
                                print(f"Error receiving action from player {player_id}: {e}")
                                retry_count += 1
                                if retry_count < RETRY_COUNT:
                                    self.send_text_message(player_id, f"Connection error. Try again. ({retry_count}/{RETRY_COUNT})")
                        
                        # If we've exhausted retries and no action was processed, automatically fold the player
                        if not action_processed and player_id in self.player_connections:
                            logger.warning(f"Player {player_id} exhausted {RETRY_COUNT} retries. Automatically folding.")
                            print(f"Player {player_id} exhausted {RETRY_COUNT} retries. Automatically folding.")
                            
                            # Force fold action
                            fold_action = PLAYER_ACTION(player_id, PokerAction.FOLD.value, 0)
                            fold_ok = self.process_action(player_id, str(fold_action))
                            
                            if fold_ok:
                                self.broadcast_text(f"Player {player_id} was automatically folded due to invalid actions")
                                logger.info(f"Player {player_id} successfully auto-folded")
                            else:
                                logger.error(f"Failed to auto-fold player {player_id}")

                        idx += 1

                # round end
                end_round = ROUND_END(get_round_name_from_enum(self.game.get_current_round()))
                self.game.end_round()
                self.broadcast_game_state()

                self.broadcast_message(end_round)

                # next round
                self.broadcast_game_state()
                self.broadcast_message(round_start_message)
                self.game.start_round()

        except Exception as e:
            logger.error(f"Error running game: {e}")
            print(f"Error running game: {e}")
        finally:
            self.game_in_progress = False

    def send_message(self, player_id, message):
        """
        Send a message to a player in raw text.
        """
        message = message + "\n"
        if player_id in self.player_connections:
            self.player_connections[player_id].sendall(message.encode('utf-8'))

    def send_text_message(self, player_id, message):
        mes = TEXT(message)
        self.send_message(player_id, mes.serialize())
        logger.debug(f"Sent message to player {player_id}: {message}")
        print(f"Sent message to player {player_id}: {message}")

    def broadcast(self, message):
        message = message + "\n"
        for _, conn in self.player_connections.items():
            conn.sendall(message.encode('utf-8'))

    def broadcast_text(self, message):
        mes = TEXT(message)
        self.broadcast(str(mes))

    def broadcast_message(self, message: Message):
        self.broadcast(message.serialize())

    def broadcast_game_state(self):
        round_name = get_round_name(self.game.round_index)
        logger.debug(f"Broadcasting game state for round {round_name}")
        print(f"Broadcasting game state for round {round_name}")

        game_state = self.game.get_game_state(self.player_money)
        message = GAME_STATE(game_state)
        
        self.broadcast(str(message))

    def process_action(self, player_id, action):
        # Process the action received from the player, broadcast the game state if successful
        action = action.strip()
        action_message = PLAYER_ACTION.parse(action)
        action_type = action_message.message["action"]
        action_amount = action_message.message["amount"]

        action_tuple = (get_poker_action_enum_from_index(action_type), action_amount)
        logger.info(f"Processing action from player {player_id}: {action_tuple}")
        print(f"Processing action from player {player_id}: {action_tuple}")
        
        # Check if player has enough money for the action (except fold and check)
        if action_type != 1 and action_type != 2:  # Not fold and not check
            current_money = self.player_money.get(player_id, 0)
            current_delta = self.player_delta.get(player_id, 0)
            
            # For CALL actions, calculate the actual amount needed
            if action_type == 3:  # CALL
                # Get the actual call amount from the game state
                current_bet = self.game.current_round.raise_amount
                player_bet = self.game.current_round.player_bets.get(player_id, 0)
                actual_call_amount = current_bet - player_bet
                
                if actual_call_amount > current_money:
                    logger.warning(f"Player {player_id} doesn't have enough money for call: needs {actual_call_amount}, has {current_money} (delta: {current_delta})")
                    print(f"Player {player_id} doesn't have enough money for call: needs {actual_call_amount}, has {current_money} (delta: {current_delta})")
                    
                    # Force them to fold due to insufficient money for call
                    logger.info(f"Forcing player {player_id} to fold due to insufficient money for call")
                    print(f"Forcing player {player_id} to fold due to insufficient money for call")
                    action_tuple = (PokerAction.FOLD, 0)
                    self.broadcast_text(f"Player {player_id} automatically folded due to insufficient money")
                    
            else:
                # For other actions (RAISE, ALL_IN), check the amount sent by client
                if action_amount > current_money:
                    logger.warning(f"Player {player_id} doesn't have enough money for action: needs {action_amount}, has {current_money} (delta: {current_delta})")
                    print(f"Player {player_id} doesn't have enough money for action: needs {action_amount}, has {current_money} (delta: {current_delta})")
                    
                    # If it's an all-in action, allow it with the amount they have
                    if action_type == 5:  # All-in
                        action_tuple = (get_poker_action_enum_from_index(action_type), current_money)
                        logger.info(f"Adjusting all-in amount to {current_money}")
                    else:
                        # For other actions, force them to fold
                        logger.info(f"Forcing player {player_id} to fold due to insufficient money")
                        print(f"Forcing player {player_id} to fold due to insufficient money")
                        action_tuple = (PokerAction.FOLD, 0)
                        self.broadcast_text(f"Player {player_id} automatically folded due to insufficient money")
        
        try:
            self.game.update_game(player_id, action_tuple)
        except Exception as e:
            self.send_text_message(player_id, f"Invalid action: {e}")
            logger.error(f"Error processing action from player {player_id}: {e}")
            print(f"Error processing action from player {player_id}: {e}")
            return False

        self.broadcast_game_state()
        return True

    def remove_player(self, player_id):
        if player_id in self.player_connections:
            self.player_connections[player_id].close()
            del self.player_connections[player_id]
            del self.player_addresses[player_id]
            logger.info(f"Player {player_id} disconnected.")
            print(f"Player {player_id} disconnected.")

    def generate_player_id(self):
        return uuid.uuid4().int & (1<<32)-1
    
    def append_to_file(self, path, score):
        with open(path, "a") as file:
            file.write(f"{score}\n")
        
        file.close()

    def remove_file_content(self, path):
        with open(path, "w") as file:
            file.write("")
        
        file.close()

    def rotate_dealer_button(self):
        """Rotate the dealer button to the next player who can afford the big blind"""
        # Get list of players who can afford the big blind
        big_blind_amount = self.blind_amount
        players_who_can_afford_blind = []
        
        for player_id in self.player_connections.keys():
            if self.can_player_afford_blind(player_id, big_blind_amount):
                players_who_can_afford_blind.append(player_id)
        
        if len(players_who_can_afford_blind) == 0:
            logger.warning("No players can afford the big blind, keeping dealer button in same position")
            print("No players can afford the big blind, keeping dealer button in same position")
            return
        
        # Find current dealer player
        all_players = list(self.player_connections.keys())
        current_dealer_player = all_players[self.dealer_button_position % len(all_players)]
        
        # Find the index of current dealer in the list of players who can afford blind
        try:
            current_dealer_index = players_who_can_afford_blind.index(current_dealer_player)
        except ValueError:
            # Current dealer can't afford blind, start from first player who can
            current_dealer_index = -1
        
        # Rotate to next player who can afford blind
        next_dealer_index = (current_dealer_index + 1) % len(players_who_can_afford_blind)
        next_dealer_player = players_who_can_afford_blind[next_dealer_index]
        
        # Update dealer button position to point to the next dealer
        next_dealer_position = all_players.index(next_dealer_player)
        self.dealer_button_position = next_dealer_position
        
        logger.info(f"Dealer button rotated to position {self.dealer_button_position} (player {next_dealer_player} who can afford big blind)")
        print(f"Dealer button rotated to position {self.dealer_button_position} (player {next_dealer_player} who can afford big blind)")

    def update_player_money_after_game(self, game_scores):
        """Update player money based on game results using delta approach"""
        for player_id, score in game_scores.items():
            if player_id in self.player_delta:
                # Update the cumulative delta
                old_delta = self.player_delta[player_id]
                self.player_delta[player_id] += score
                new_delta = self.player_delta[player_id]
                
                # Calculate money as initial_money + delta
                old_money = self.player_money[player_id]
                self.player_money[player_id] = self.initial_money + new_delta
                new_money = self.player_money[player_id]
                
                logger.info(f"Player {player_id} delta updated: {old_delta} + {score} = {new_delta}, money: {old_money} -> {new_money}")
                print(f"Player {player_id} delta updated: {old_delta} + {score} = {new_delta}, money: {old_money} -> {new_money}")
                
                # Ensure money doesn't go below 0 (players can have negative money from blinds)
                if self.player_money[player_id] < 0:
                    logger.info(f"Player {player_id} has negative money: {self.player_money[player_id]}")
                    print(f"Player {player_id} has negative money: {self.player_money[player_id]}")

    def can_player_afford_blind(self, player_id, blind_amount):
        """Check if a player can afford to post a blind"""
        current_money = self.player_money.get(player_id, 0)
        current_delta = self.player_delta.get(player_id, 0)
        can_afford = current_money >= blind_amount
        logger.debug(f"Player {player_id} can afford {blind_amount}: {can_afford} (money: {current_money}, delta: {current_delta})")
        return can_afford

