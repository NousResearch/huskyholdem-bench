import json
import socket
import logging
from typing import Optional, Any

from type.utils import get_message_type_name

from config import START_MONEY, GAMEID_LOG_FILE
from type.message import MessageType
from type.round_state import RoundStateClient
from type.poker_action import PokerAction

class Runner:
    """
    Client runner that connects to a poker server and handles the game flow.
    """
    def __init__(self, host: str, port: int,  result_path: str, sim: bool = False) -> None:
        """
        Initialize the runner with connection details.
        
        Args:
            host: Server hostname or IP address
            port: Server port
        """
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bot = None
        self.current_round: Optional[RoundStateClient] = None
        self.player_id = None
        self.logger = self._setup_logger()
        self.initial_money = START_MONEY
        self.player_money = START_MONEY
        self.player_delta = 0  # Track cumulative delta (change from initial money)

        self.run_success = False
        self.points = 0
        self.result_path = result_path

        # Simulation mode
        self.sim = sim
        
        # Multi-game support
        self.game_count = 0
        self.total_points = 0
        
        # Blind information
        self.blind_amount = 0
        self.is_small_blind = False
        self.is_big_blind = False
        self.blind_posted = False
        
        # Track previous round actions for all-in detection
        self.previous_round_action = None
        self.current_round_number = 0

    @staticmethod
    def _setup_logger():
        """Set up logging configuration."""
        logger = logging.getLogger('PokerRunner')
        
        # Always use the root logger configuration set up by main.py
        # This ensures consistent dual logging (console + file)
        return logger
    
    def get_score(self) -> int:
        """
        Get the score of the current game.
        
        Returns:
            int: Player's current game score
        """
        return self.points

    def get_total_score(self) -> int:
        """
        Get the total score across all games.
        
        Returns:
            int: Player's total score across all games
        """
        return self.total_points

    def get_game_count(self) -> int:
        """
        Get the number of games played.
        
        Returns:
            int: Number of games played
        """
        return self.game_count

    def set_bot(self, bot):
        """
        Set the bot instance that will play the game.
        
        Args:
            bot: Instance of a poker-playing bot
        """
        self.bot = bot

    def _process_message(self, json_message: dict) -> None:
        """
        Process a single JSON message from the server.
        
        Args:
            json_message: Parsed JSON message from server
        """
        message_type = json_message.get('type')
        message = json_message.get('message')
        
        if message_type is None:
            self.logger.error("Invalid message: missing type")
            return
            
        message_type_name = get_message_type_name(message_type)
        self.logger.info(f"Received message type: {message_type_name}")
        
        handlers = {
            MessageType.CONNECT.value: self._handle_connect,
            MessageType.GAME_START.value: self._handle_game_start,
            MessageType.GAME_STATE.value: self._handle_game_state,
            MessageType.ROUND_START.value: self._handle_round_start,
            MessageType.REQUEST_PLAYER_ACTION.value: self._handle_request_action,
            MessageType.ROUND_END.value: self._handle_round_end,
            MessageType.GAME_END.value: self._handle_game_end,
            MessageType.MESSAGE.value: self._handle_txt,  # Ignore generic messages
        }
        
        handler = handlers.get(message_type)
        if handler:
            handler(message)
        else:
            self.logger.warning(f"No handler for message type: {message_type}")

    def _handle_txt(self, message: Any) -> None:
        """Handle text message."""
        self.logger.info(f"Server: {message}")

    def _handle_connect(self, message: Any) -> None:
        """Handle connection confirmation message."""
        self.player_id = message
        self.bot.set_id(self.player_id)
        self.logger.info(f"Connected with player ID: {self.player_id}")
        
        # Log player ID to gameid.log file
        self.write_to_file(GAMEID_LOG_FILE, f"Player connected: {self.player_id}")

    def _handle_game_start(self, message: Any) -> None:
        """Handle game start message."""
        hands = message['hands']
        # Extract blind information from the message
        self.blind_amount = message.get('blind_amount', 0)
        self.is_small_blind = message.get('is_small_blind', False)
        self.is_big_blind = message.get('is_big_blind', False)
        self.blind_posted = False  # Reset blind posted flag for new game
        
        # Extract blind player IDs
        small_blind_player_id = message.get('small_blind_player_id', None)
        big_blind_player_id = message.get('big_blind_player_id', None)
        
        # Extract all players list
        all_players = message.get('all_players', [])
        
        if self.bot:
            self.bot.on_start(self.player_money, hands, self.blind_amount, big_blind_player_id, small_blind_player_id, all_players)
        self.logger.info(f"Game #{self.game_count + 1} started with {len(hands)} cards, blind: {self.blind_amount}")
        self.logger.info(f"All players in game: {all_players}")
        self.logger.info(f"Small blind player: {small_blind_player_id}, Big blind player: {big_blind_player_id}")
        if self.is_small_blind:
            self.logger.info("This player is the small blind")
        elif self.is_big_blind:
            self.logger.info("This player is the big blind")
            
        # update player money with blind
        # Check if this player needs to post a blind and hasn't done so yet
        if not self.blind_posted and (self.is_small_blind or self.is_big_blind):
            if self.is_small_blind:
                blind_amount = self.blind_amount // 2
                self.logger.info(f"Automatically posting small blind: {blind_amount}")
                # self.send_action_to_server(self.player_id, 4, blind_amount)  # raise action
                self.player_money -= blind_amount
                self.blind_posted = True
            elif self.is_big_blind:
                blind_amount = self.blind_amount
                self.logger.info(f"Automatically posting big blind: {blind_amount}")
                # self.send_action_to_server(self.player_id, 4, blind_amount)  # raise action
                self.player_money -= blind_amount
                self.blind_posted = True

    def _handle_game_state(self, message: dict) -> None:
        """Handle game state message."""
        if self.bot:
            # Update player money from server if available
            if 'player_money' in message and message['player_money'] and str(self.player_id) in message['player_money']:
                server_money = message['player_money'][str(self.player_id)]
                if server_money != self.player_money:
                    self.logger.info(f"Updating money from server: {self.player_money} -> {server_money}")
                    self.player_money = server_money
                    # Recalculate delta based on server money
                    self.player_delta = self.player_money - self.initial_money
            
            self.current_round = RoundStateClient.from_message(message)
            self.logger.debug(f"Updated game state: round {message['round_num']}")
            if message.get('side_pots'):
                self.logger.info(f"Side pots active: {len(message['side_pots'])} pot(s)")
                for i, pot in enumerate(message['side_pots']):
                    self.logger.info(f"  Pot {i}: {pot['amount']} chips, eligible players: {pot['eligible_players']}")

    def _handle_round_start(self, message: Any) -> None:
        """Handle round start message."""
        # Extract round number from message if available
        if hasattr(message, 'round_num') and message.round_num is not None:
            self.current_round_number = message.round_num
            self.logger.info(f"Round {self.current_round_number} started")
        else:
            self.current_round_number += 1
            self.logger.info(f"Round {self.current_round_number} started")
            
        if self.bot and self.current_round:
            self.bot.on_round_start(self.current_round, self.player_money)

    def _handle_request_action(self, _: Any) -> None:
        """Handle request for player action."""
        if not self.bot or not self.current_round:
            self.logger.error("No bot or current round available")
            return
        
        # Check if this player was all-in in the previous round and automatically respond with ALL_IN
        if self.current_round_number > 0 and self.previous_round_action == PokerAction.ALL_IN:
            self.logger.info(f"Player was all-in in previous round. Automatically responding with ALL_IN (amount: 0)")
            self.send_action_to_server(self.player_id, 5, 0)  # ALL_IN with 0 amount
            return
            
        try:
            action, amount = self.bot.get_action(self.current_round, self.player_money)
            self.logger.info(f"Bot action: {action.name}, amount: {amount}")
            
            ok = self._validate_action(action.value, amount)
            if not ok:
                self.logger.error("Invalid action or amount")
                # punish the bot for invalid action
                if self.previous_round_action == PokerAction.ALL_IN:
                    self.send_action_to_server(self.player_id, 5, 0)  # all-in
                else:
                    self.send_action_to_server(self.player_id, 1, 0)  # fold
                return
            
            # Check if raise action uses all player's money - convert to all-in
            if action.value == 4:  # RAISE
                actual_raise_amount = amount + self.current_round.player_bets[str(self.player_id)]
                if actual_raise_amount >= self.player_money:
                    self.logger.info(f"Converting raise to all-in: {action.name} -> ALL_IN")
                    action = PokerAction.ALL_IN
                    amount = self.player_money
            
            # For CALL actions, calculate actual call amount and send to server
            if action.value == 3:  # CALL
                # Calculate actual call amount for local money tracking
                actual_call_amount = self.current_round.current_bet - self.current_round.player_bets[str(self.player_id)]
                
                if actual_call_amount >= self.player_money:
                    self.logger.info(f"Player is all-in: {action.name} -> ALL_IN")
                    action = PokerAction.ALL_IN
                    amount = self.player_money
                    self.send_action_to_server(self.player_id, action.value, amount)
                    self.player_money -= amount
                    return
                else:
                    if actual_call_amount < 0:
                        self.logger.error(f"Invalid call action: cannot afford {actual_call_amount}, have {self.player_money}")
                        if self.previous_round_action == PokerAction.ALL_IN:
                            self.send_action_to_server(self.player_id, 5, 0)  # all-in
                        else:
                            self.send_action_to_server(self.player_id, 1, 0)  # fold
                        return
                    self.send_action_to_server(self.player_id, action.value, actual_call_amount)
                    self.player_money -= actual_call_amount  # Deduct actual amount locally
            # For ALL_IN actions, calculate actual all-in amount and send to server
            elif action.value == 5:  # ALL_IN
                # All-in amount is the player's remaining money
                actual_allin_amount = self.player_money
                self.send_action_to_server(self.player_id, action.value, actual_allin_amount)
                self.player_money -= actual_allin_amount  # Deduct actual amount locally
            else:
                # For other actions, send the amount and deduct locally
                self.send_action_to_server(self.player_id, action.value, amount)
                self.player_money -= amount
            
            # Store the action for next round's all-in detection
            self.previous_round_action = action

        except Exception as e:
            self.logger.exception(f"Error in get_action: {e}")
            # Fold on any exception
            if self.previous_round_action == PokerAction.ALL_IN:
                self.send_action_to_server(self.player_id, 5, 0)  # all-in
            else:
                self.send_action_to_server(self.player_id, 1, 0)  # fold
            return

    def _handle_round_end(self, _: Any) -> None:
        """Handle round end message."""
        if self.bot and self.current_round:
            self.bot.on_end_round(self.current_round, self.player_money)
        self.logger.info("Round ended")

    def _handle_game_end(self, message: Any) -> None:
        """Handle game end message."""
        if self.bot and self.current_round:
            player_score = message.get('player_score', 0)
            all_scores = message.get('all_scores', {})
            active_players_hands = message.get('active_players_hands', {})
            self.points = int(player_score)
            self.logger.info(f"All final scores: {all_scores}")
            self.logger.info(f"Active players hands: {active_players_hands}")
            # Always log game results regardless of simulation mode
            self.append_to_file(self.result_path, f"Game_{self.game_count + 1}: Player score: {player_score}, All scores: {all_scores}")
            
            # Update player delta and money based on game result using delta approach
            old_delta = self.player_delta
            self.player_delta += player_score
            old_money = self.player_money
            self.player_money = self.initial_money + self.player_delta
            self.logger.info(f"Delta updated: {old_delta} + {player_score} = {self.player_delta}, money: {old_money} -> {self.player_money}")
            
            self.bot.on_end_game(self.current_round, player_score, all_scores, active_players_hands)
            self.total_points += self.points
            self.run_success = True
        self.logger.info(f"Game #{self.game_count + 1} ended with score: {self.points}")
        
        # Reset for next game instead of closing connection
        self.reset_for_new_game()

    def handle_messages(self, message_data: str) -> None:
        """
        Process raw message data from the server.
        
        Args:
            message_data: Raw message string from server
        """
        lines = message_data.split('\n')
        for line in lines:
            if not line:  # Skip empty lines
                continue
                
            try:
                json_message = json.loads(line)
                self._process_message(json_message)
            except json.JSONDecodeError:
                self.logger.error(f"Error decoding message: {line}")
            except Exception as e:
                self.logger.exception(f"Error processing message: {e}")

    def _validate_action(self, action: int, amount: int) -> bool:

        """
        Validate the action and amount before sending to server.
        
        Args:
            action: Action code (from MessageType enum)
            amount: Bet amount

        """

        if amount < 0:
            self.logger.error("Invalid amount: cannot be negative")
            return False
        
        # fold - always valid, even with no money
        if action == 1:
            return True
        
        # check - always valid if current bet is zero
        if action == 2:
            if self.current_round and self.current_round.current_bet == 0:
                return True
            else:
                self.logger.error("Invalid check action: current bet is not zero")
                return False

        # For actions that require money, check if player has enough
        if amount > self.player_money:
            self.logger.warning(f"Player doesn't have enough money for action: needs {amount}, has {self.player_money}")
            # Allow the action to proceed - the server will handle insufficient funds
            # This allows for all-in scenarios where player bets all they have
            return True

        # call - validate that player can afford the actual call amount
        if action == 3:
            if self.current_round:
                actual_call_amount = self.current_round.current_bet - self.current_round.player_bets[str(self.player_id)]
                if actual_call_amount >= 0 and actual_call_amount <= self.player_money:
                    return True
                else:
                    self.logger.error(f"Invalid call action: cannot afford {actual_call_amount}, have {self.player_money}")
                    return False
            return False
            
        # raise
        if action == 4:
            actual_raise = amount + self.current_round.player_bets[str(self.player_id)]

            if self.current_round and actual_raise >= self.current_round.current_bet:
                return True
            else:
                self.logger.error("Invalid raise action: amount out of range")
                return False
            
        # all in - validate that player has money to go all-in
        if action == 5:
            if self.current_round and self.player_money > 0:
                return True
            else:
                self.logger.error("Invalid all-in action: player has no money")
                return False
            
        return True

    def send_action_to_server(self, player_id: str, action: int, amount: int) -> None:
        """
        Send player action to the server.
        
        Args:
            player_id: The ID of the player
            action: Action code (from MessageType enum)
            amount: Bet amount
        """
        message = {
            'type': MessageType.PLAYER_ACTION.value,
            'message': {
                'player_id': player_id,
                'action': action,
                'amount': amount
            }
        }

        try:
            self.client_socket.send(json.dumps(message).encode('utf-8'))
            self.logger.debug(f"Sent action: {action}, amount: {amount}")
        except Exception as e:
            self.logger.error(f"Failed to send action: {e}")

    def receive_messages(self) -> None:
        """Receive and process messages from the server."""
        sock_file = self.client_socket.makefile('r')
        while True:
            try:
                line = sock_file.readline()
                if not line:
                    self.logger.info("Server closed connection")
                    break
                self.handle_messages(line.strip())
            except Exception as e:
                self.logger.error(f"Error decoding message: {e}")

    def connect(self) -> bool:
        """
        Connect to the poker server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client_socket.connect((self.host, self.port))
            self.logger.info(f"Connected to server at {self.host}:{self.port}")
            return True
        except socket.error as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    def run(self) -> None:
        """Run the client, connecting to server and handling messages."""
        if not self.bot:
            self.logger.error("No bot set. Use set_bot() before running.")
            return
            
        if not self.connect():
            return
            
        try:
            self.receive_messages()
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        finally:
            self.close()

    def append_to_file(self, filename: str, data: str) -> None:
        """Append data to a file."""
        try:
            with open(filename, 'a') as file:
                file.write(data + '\n')
            self.logger.info(f"Data appended to {filename}")
        except Exception as e:
            self.logger.error(f"Error writing to file {filename}: {e}")

    def write_to_file(self, filename: str, data: str) -> None:
        """Overwrite data to a file."""
        try:
            with open(filename, 'w') as file:
                file.write(data + '\n')
            self.logger.info(f"Data written to {filename}")
        except Exception as e:
            self.logger.error(f"Error writing to file {filename}: {e}")

    def close(self) -> None:
        """Close the connection to the server."""
        try:
            self.client_socket.close()
            self.logger.info("Connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")

    def reset_for_new_game(self):
        """Reset client state for a new game"""
        self.current_round = None
        # Don't reset player_money or player_delta - keep them from previous game
        # self.player_money = START_MONEY  # Removed this line
        # self.player_delta = 0  # Removed this line
        self.points = 0
        self.game_count += 1
        # Reset blind information for new game
        self.blind_amount = 0
        self.is_small_blind = False
        self.is_big_blind = False
        self.blind_posted = False
        # Reset all-in tracking for new game
        self.previous_round_action = None
        self.current_round_number = 0
        self.logger.info(f"Reset for Game #{self.game_count}, current money: {self.player_money}, delta: {self.player_delta}")