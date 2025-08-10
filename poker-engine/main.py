import argparse
import logging
import os
import glob
from server import PokerEngineServer
from config import NUM_ROUNDS, OUTPUT_FILE_SIMULATION, OUTPUT_GAME_RESULT_FILE, BASE_PATH

def cleanup_game_logs():
    """Remove all existing game_log files before starting a new run"""
    try:
        # Find all game_log*.json files in the BASE_PATH directory
        game_log_pattern = os.path.join(BASE_PATH, "game_log_*.json")
        game_log_files = glob.glob(game_log_pattern)
        
        if game_log_files:
            print(f"Cleaning up {len(game_log_files)} existing game log files...")
            for file_path in game_log_files:
                try:
                    os.remove(file_path)
                    print(f"Removed: {os.path.basename(file_path)}")
                except OSError as e:
                    print(f"Warning: Could not remove {file_path}: {e}")
        else:
            print("No existing game log files to clean up.")
            
    except Exception as e:
        print(f"Warning: Error during game log cleanup: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Poker Engine Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--players', type=int, default=2, help='Number of players')
    parser.add_argument('--timeout', type=int, default=30, help='Turn timeout in seconds')
    parser.add_argument('--debug', default=False, action='store_true', help='Enable debug mode')
    parser.add_argument('--sim', default=False, action='store_true', help='Enable simulation mode')
    parser.add_argument('--sim-rounds', type=int, default=NUM_ROUNDS, help='Number of rounds to simulate')
    parser.add_argument('--blind', type=int, default=10, help='Blind amount for the game')
    parser.add_argument('--log-file', type=str, default=None, help='Log file path (if not specified, logs to console)')
    parser.add_argument('--blind-multiplier', type=float, default=1.0, help='Factor to multiply blind amount by (default: 1.0 = no increase)')
    parser.add_argument('--blind-increase-interval', type=int, default=0, help='Number of games after which to increase blinds (default: 0 = never increase)')
    args = parser.parse_args()

    # Clean up existing game log files before starting
    cleanup_game_logs()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    if args.log_file:
        # Log to file
        logging.basicConfig(
            filename=args.log_file,
            level=log_level,
            format=log_format,
            filemode='w'  # Overwrite the file each time
        )
        print(f"Logging to file: {args.log_file}")
    else:
        # Log to console
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
        print("Logging to console")

    # Get the logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Poker Engine Server starting...")

    # simulation mode
    if args.sim:
        try:
            # Write RUNNING when starting simulation
            with open(OUTPUT_FILE_SIMULATION, 'w') as sim_file:
                sim_file.write("RUNNING\n")

            logger.info(f"Starting continuous simulation mode for {args.sim_rounds} games")
            print(f"Starting continuous simulation mode for {args.sim_rounds} games")
            # Create one server that runs multiple games
            server = PokerEngineServer(args.host, args.port, args.players, args.timeout, args.debug, args.sim, args.blind, args.blind_multiplier, args.blind_increase_interval)
            server.simulation_rounds = args.sim_rounds  # Add this attribute to track rounds
            server.start_server()

        except KeyboardInterrupt:
            logger.info("Shutting down simulation...")
            print("Shutting down simulation...")
            if 'server' in locals():
                server.stop_server()
     
    # normal mode - run 1 game and write to game_result file
    else:
        try:
            # Write RUNNING when starting single game
            with open(OUTPUT_GAME_RESULT_FILE, 'w') as game_file:
                game_file.write("RUNNING\n")

            logger.info("Starting single game mode")
            print("Starting single game mode")
            # Create server that runs 1 game (sim=False to use game_result output)
            server = PokerEngineServer(args.host, args.port, args.players, args.timeout, args.debug, False, args.blind, args.blind_multiplier, args.blind_increase_interval)
            server.simulation_rounds = 1  # Set to run only 1 game
            server.start_server()

        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            print("Shutting down server...")
            if 'server' in locals():
                server.stop_server()
