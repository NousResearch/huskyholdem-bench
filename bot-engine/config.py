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

# Network configuration
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 5000

START_MONEY = 10000
RESULT_FILE = os.path.join(BASE_PATH, 'game_result.log')

# Logging configuration
CLIENT_LOG_FILE = os.path.join(BASE_PATH, 'poker_client.log')
GAMEID_LOG_FILE = os.path.join(BASE_PATH, 'gameid.log')