import logging
from app.service.docker.shared_manager import SharedDockerPoolManager
from app.service.cache.redis import RedisService
from app.config.setting import settings

logger = logging.getLogger(__name__)

def initialize_docker_pool():
    """Initialize the Docker container pool on application startup."""
    try:
        logger.info("Initializing shared Docker container pool...")
        pool_manager = SharedDockerPoolManager()
        
        # Get initial status
        status = pool_manager.get_pool_status()
        logger.info(f"Shared Docker pool initialized successfully. Status: {status}")
        
        return pool_manager
    except Exception as e:
        logger.error(f"Failed to initialize shared Docker pool: {e}")
        raise

def shutdown_docker_pool():
    """Shutdown the Docker container pool and clean up Redis state on application shutdown."""
    try:
        logger.info("Shutting down shared Docker container pool...")
        
        # Clean up Redis state
        try:
            redis_service = RedisService()
            
            # Clear pool-related Redis keys
            redis_keys_to_clear = [
                "docker_pool:containers",
                "docker_pool:active", 
                "docker_pool:lock",
                "docker_pool:initialized",
                "docker_pool:monitor_lock",
                "docker_pool:scaling_lock"
            ]
            
            for key in redis_keys_to_clear:
                redis_service.remove(key)
                logger.info(f"Cleared Redis key: {key}")
                
            logger.info("Redis cleanup completed")
            
        except Exception as redis_error:
            logger.error(f"Error during Redis cleanup: {redis_error}")
        
        # Shutdown the pool manager
        try:
            pool_manager = SharedDockerPoolManager()
            pool_manager.shutdown()
            logger.info("Shared Docker pool shutdown complete")
        except Exception as pool_error:
            logger.error(f"Error during pool shutdown: {pool_error}")
            
    except Exception as e:
        logger.error(f"Error during Docker pool shutdown: {e}")

def cleanup_all_redis_docker_state():
    """Emergency cleanup function to clear all Docker-related Redis state."""
    try:
        logger.info("Performing emergency cleanup of all Docker-related Redis state...")
        redis_service = RedisService()
        
        # Get all Redis keys and filter for Docker pool related ones
        try:
            # Use Redis client directly to get all keys with pattern
            all_keys = redis_service.client.keys("docker_pool:*")
            
            if all_keys:
                redis_service.client.delete(*all_keys)
                logger.info(f"Cleared {len(all_keys)} Docker pool Redis keys: {all_keys}")
            else:
                logger.info("No Docker pool Redis keys found to clear")
                
        except Exception as e:
            logger.error(f"Error getting Redis keys: {e}")
            # Fallback to manually clearing known keys
            known_keys = [
                "docker_pool:containers",
                "docker_pool:active", 
                "docker_pool:lock",
                "docker_pool:initialized",
                "docker_pool:monitor_lock",
                "docker_pool:scaling_lock"
            ]
            
            for key in known_keys:
                try:
                    redis_service.remove(key)
                    logger.info(f"Cleared Redis key: {key}")
                except Exception as key_error:
                    logger.error(f"Error clearing key {key}: {key_error}")
        
        logger.info("Emergency Redis cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during emergency Redis cleanup: {e}")
        raise 