from pydantic_settings import BaseSettings
import os

from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "The betting edge"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_DESCRIPTION: str = "A betting edge API"
    DOCKER_SOCKET: str = "/var/run/docker.sock"

    GAME_ENGINE_IMAGE: str = "kipiiler75/huskyholdem-gengine:latest"
    RUNNER_IMAGE: str = "kipiiler75/huskyholdem-runner:latest"

    GAME_ENGINE_PORT_START: int = 5000
    GAME_ENGINE_PORT_END: int = 7000

    GAME_NETWORK_NAME: str = "husky_game_network"

    BOT_NUMBER_PER_GAME_SIMULATION: int = 5
    NUM_PLAYERS_PER_GAME: int = 6

    RABBITMQ_URL    : str = "amqp://guest:guest@rabbit-mq:5672/"
    WORKER_RETRY_COUNT: int = 3
    WORKER_RETRY_DELAY: int = 5  # seconds

    GAME_RUN_TIMEOUT: int = 60*60*2  # seconds (2 hours)

    MAX_JOB_RUNNING_PER_USER: int = 2

    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "YOUR_SENDGRID_API_KEY_HERE")
    MAIL_FROM_EMAIL: str = os.getenv("MAIL_FROM_EMAIL", "uwfeclub@gmail.com")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis")
    API_URL: str = os.getenv("API_URL", "http://localhost:8002")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    VERIFIED_TOKEN_TTL: int = 30*60
    # Docker Pool Management Settings
    DOCKER_POOL_SIZE: int = 7  # Number of idle game server containers to maintain
    DOCKER_POOL_MONITOR_INTERVAL: int = 30  # Seconds between pool health checks
    DOCKER_CONTAINER_ACQUISITION_TIMEOUT: int = 30  # Seconds to wait for available container
    DOCKER_POOL_MAX_RETRIES: int = 3  # Max retries when no containers available
    SCALE_DOCKER_MAX_RETRIES: int = 3

    SAFE_EXEC_TIMEOUT: int = 60 * 60 *2 # 2 hours

    # Tournament 2025
    TOURNAMENT_2025_TAG: str = "tournament_2025"

settings = Settings()