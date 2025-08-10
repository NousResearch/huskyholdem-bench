import argparse
import os
from time import sleep
from config import RESULT_FILE, DEFAULT_HOST, DEFAULT_PORT, CLIENT_LOG_FILE
from runner import Runner
import logging

from player import SimplePlayer


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, log_file_path: str = None, result_path=RESULT_FILE, simulation: bool = False, simulation_round: int = 6, local: bool = False, debug: bool = False) -> None:
    """Main entry point for the poker bot runner."""
    
    # Configure logging - always log to both console and file
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Use specified log file or default to CLIENT_LOG_FILE
    file_path = log_file_path or CLIENT_LOG_FILE
    
    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set up file handler
    file_handler = logging.FileHandler(file_path, mode='w')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    print(f"Client logging to console and file: {file_path}")

    # Get the logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Poker Client starting...")
    
    # clear the result file
    if os.path.exists(result_path):
        os.remove(result_path)

    if local:
        print("Running in local mode, saving results to local file")
        result_path = 'game_result.log'

    if simulation:
        logger.info(f"Running in continuous simulation mode for {simulation_round} games")
        print(f"Running in continuous simulation mode for {simulation_round} games")
        # Create one runner that plays multiple games
        runner = Runner(host, port, result_path, simulation)
        simple_bot = SimplePlayer()
        runner.set_bot(simple_bot)
        runner.run()
        
        # Get final statistics
        total_games = runner.get_game_count()
        total_score = runner.get_total_score()
        logger.info(f"Continuous simulation completed. Total games played: {total_games}")
        logger.info(f"Total score: {total_score}")
        print(f"Continuous simulation completed. Total games played: {total_games}")
        print(f"Total score: {total_score}")
        if total_games > 0:
            logger.info(f"Average score per game: {total_score / total_games}")
            print(f"Average score per game: {total_score / total_games}")
            runner.append_to_file(result_path, f"CONTINUOUS_MODE \n Games: {total_games}, \n Total: {total_score}, \n Average: {total_score / total_games}")

    else:
        logger.info("Running single game mode")
        print("Running single game mode")
        runner = Runner(host, port, result_path, simulation)
        simple_bot = SimplePlayer()
        runner.set_bot(simple_bot)
        runner.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poker Bot Runner")
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help='Server host')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Server port')
    parser.add_argument('--log-file', type=str, default=None, help='Log file path (if not specified, logs to console)')
    parser.add_argument('-r', '--result', type=str, default=RESULT_FILE, help='File to save the result')
    parser.add_argument('-s', '--simulation', type=bool, default=False, help='Run in simulation mode')
    parser.add_argument('-sr', '--simulation_rounds', type=int, default=6, help='Number of rounds in simulation mode')
    parser.add_argument('-l', '--local', type=bool, default=False, help='Run in local mode')
    parser.add_argument('--debug', default=False, action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    # Run the main function with command line arguments
    try:
        main(args.host, args.port, args.log_file, args.result, args.simulation, args.simulation_rounds, args.local, args.debug)
    except KeyboardInterrupt:
        print("\nExiting...")