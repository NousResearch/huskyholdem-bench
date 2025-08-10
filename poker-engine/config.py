import os

# Environment detection
IS_DOCKER = os.path.exists('/.dockerenv')

# Base paths for different environments
DOCKER_BASE_PATH = "/app/output"
LOCAL_BASE_PATH = "output"

# Use appropriate base path based on environment
BASE_PATH = DOCKER_BASE_PATH if IS_DOCKER else LOCAL_BASE_PATH

# Ensure output directory exists in all environments
os.makedirs(BASE_PATH, exist_ok=True)

NUM_ROUNDS = 6
SERVER_SIM_WAIT_BETWEEN_GAMES = 0.01 # seconds, time to wait between games in simulation mode
OUTPUT_GAME_RESULT_FILE = os.path.join(BASE_PATH, "game_result.log")
OUTPUT_FILE_SIMULATION = os.path.join(BASE_PATH, "sim_result.log")
RETRY_COUNT = 1

# Server configuration
HOST = 'localhost'
PORT = 5000
DEFAULT_NUM_PLAYERS = 2
DEFAULT_TURN_TIMEOUT = 5
DEFAULT_BLIND_AMOUNT = 10
DEFAULT_BLIND_MULTIPLIER = 1.0
DEFAULT_BLIND_INCREASE_INTERVAL = 0
DEFAULT_INITIAL_MONEY = 10000