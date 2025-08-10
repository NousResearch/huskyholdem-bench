import time
import threading
import logging
from collections import deque
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

from app.models.game import GameStatus
from app.service.docker.main import DockerService
from app.config.setting import settings

logger = logging.getLogger(__name__)


class ContainerState(Enum):
    IDLE = "idle"
    ACQUIRED = "acquired"
    RUNNING = "running"
    CLEANING = "cleaning"


@dataclass
class PooledContainer:
    port: int
    container_name: str
    state: ContainerState
    acquired_at: Optional[float] = None
    acquired_by: Optional[str] = None


class DockerPoolManager:
    """
    Manages a pool of idle game server containers for efficient resource utilization.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DockerPoolManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        
        self.docker_service = DockerService()
        self.pool: deque[PooledContainer] = deque()
        self.active_containers: Dict[int, PooledContainer] = {}
        self.pool_lock = threading.Lock()
        self.running = True
        self.sim_mode = True  # Default to simulation mode
        
        # Initialize the pool
        self._init_pool()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_pool, daemon=True)
        self.monitor_thread.start()
        
        self._initialized = True
        logger.info(f"DockerPoolManager initialized with pool size {settings.DOCKER_POOL_SIZE}")

    def _init_pool(self):
        """Initialize the container pool with idle game servers."""
        logger.info(f"Initializing container pool with {settings.DOCKER_POOL_SIZE} containers")
        for _ in range(settings.DOCKER_POOL_SIZE):
            self._add_container_to_pool()

    def _add_container_to_pool(self) -> bool:
        """Add a new container to the pool."""
        try:
            port = self.docker_service.generate_random_port()
            container_name = self.docker_service.get_game_server_container_name(port)
            
            # Create the container without starting the game server process
            success = self.docker_service.create_idle_game_server(port)
            if not success:
                logger.error(f"Failed to create idle game server on port {port}")
                self.docker_service.release_port(port)
                return False
            
            # Create pooled container object
            pooled_container = PooledContainer(
                port=port,
                container_name=container_name,
                state=ContainerState.IDLE
            )
            
            with self.pool_lock:
                self.pool.append(pooled_container)
            
            logger.info(f"Added idle container {container_name} (port {port}) to pool")
            return True
            
        except Exception as e:
            logger.error(f"Error adding container to pool: {e}")
            return False

    def acquire_container(self, worker_id: str, timeout: Optional[int] = None) -> Optional[int]:
        """
        Acquire a container from the pool.
        
        Args:
            worker_id: Identifier for the worker requesting the container
            timeout: Timeout in seconds to wait for available container
            
        Returns:
            Port number of the acquired container, or None if no container available
        """
        if timeout is None:
            timeout = settings.DOCKER_CONTAINER_ACQUISITION_TIMEOUT
        
        start_time = time.time()
        retries = 0
        
        while time.time() - start_time < timeout and retries < settings.DOCKER_POOL_MAX_RETRIES:
            with self.pool_lock:
                if self.pool:
                    # Get container from pool
                    pooled_container = self.pool.popleft()
                    pooled_container.state = ContainerState.ACQUIRED
                    pooled_container.acquired_at = time.time()
                    pooled_container.acquired_by = worker_id
                    
                    # Add to active containers
                    self.active_containers[pooled_container.port] = pooled_container
                    
                    logger.info(f"Container {pooled_container.container_name} (port {pooled_container.port}) "
                              f"acquired by worker {worker_id}")
                    return pooled_container.port
                
                # No containers available, try to add one
                if self._add_container_to_pool():
                    continue
            
            # Wait a bit before retrying
            time.sleep(1)
            retries += 1
        
        logger.warning(f"Worker {worker_id} failed to acquire container after {retries} retries")
        return None

    def release_container(self, port: int, worker_id: str, cleanup: bool = True) -> bool:
        """
        Release a container back to the pool or clean it up.
        
        Args:
            port: Port number of the container to release
            worker_id: ID of the worker releasing the container
            cleanup: Whether to clean the container before returning to pool
            
        Returns:
            True if successful, False otherwise
        """
        with self.pool_lock:
            if port not in self.active_containers:
                logger.warning(f"Container on port {port} not found in active containers")
                return False
            
            pooled_container = self.active_containers[port]
            
            # Verify ownership
            if pooled_container.acquired_by != worker_id:
                logger.warning(f"Worker {worker_id} trying to release container owned by {pooled_container.acquired_by}")
                return False
            
            # Remove from active containers
            del self.active_containers[port]
            
            try:
                if cleanup:
                    # Clean the container
                    pooled_container.state = ContainerState.CLEANING
                    self.docker_service.clean_container_internal(pooled_container.container_name)
                
                # Reset container state
                pooled_container.state = ContainerState.IDLE
                pooled_container.acquired_at = None
                pooled_container.acquired_by = None
                
                # Return to pool
                self.pool.append(pooled_container)
                
                logger.info(f"Container {pooled_container.container_name} (port {port}) "
                          f"released by worker {worker_id} and returned to pool")
                return True
                
            except Exception as e:
                logger.error(f"Error releasing container on port {port}: {e}")
                # If cleanup failed, remove the container entirely
                self._remove_container_from_pool(pooled_container)
                return False

    def _remove_container_from_pool(self, pooled_container: PooledContainer):
        """Remove a container from the pool and clean up resources."""
        try:
            self.docker_service.stop_and_remove_container(pooled_container.container_name)
            self.docker_service.release_port(pooled_container.port)
            logger.info(f"Removed container {pooled_container.container_name} from pool")
        except Exception as e:
            logger.error(f"Error removing container {pooled_container.container_name}: {e}")

    def get_pool_status(self) -> Dict:
        """Get current status of the container pool."""
        with self.pool_lock:
            return {
                "pool_size": len(self.pool),
                "active_containers": len(self.active_containers),
                "total_containers": len(self.pool) + len(self.active_containers),
                "target_pool_size": settings.DOCKER_POOL_SIZE,
                "idle_containers": len([c for c in self.pool if c.state == ContainerState.IDLE]),
                "acquired_containers": len([c for c in self.active_containers.values() if c.state == ContainerState.ACQUIRED]),
                "running_containers": len([c for c in self.active_containers.values() if c.state == ContainerState.RUNNING])
            }

    def _monitor_pool(self):
        """Monitor and maintain the container pool."""
        while self.running:
            try:
                with self.pool_lock:
                    # Ensure minimum pool size
                    while len(self.pool) < settings.DOCKER_POOL_SIZE:
                        if not self._add_container_to_pool():
                            logger.error("Failed to add container to pool during monitoring")
                            break
                    
                    # Prune excess containers
                    while len(self.pool) > settings.DOCKER_POOL_SIZE + 2:
                        pooled_container = self.pool.pop()
                        self._remove_container_from_pool(pooled_container)
                    
                    # Check for stale acquired containers
                    current_time = time.time()
                    stale_containers = []
                    for port, container in self.active_containers.items():
                        if (container.acquired_at and 
                            current_time - container.acquired_at > settings.GAME_RUN_TIMEOUT + 60):
                            logger.warning(f"Container on port {port} appears to be stale, removing")
                            stale_containers.append(port)
                    
                    for port in stale_containers:
                        container = self.active_containers.pop(port)
                        self._remove_container_from_pool(container)
                
                time.sleep(settings.DOCKER_POOL_MONITOR_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in pool monitoring: {e}")
                time.sleep(10)

    def shutdown(self):
        """Shutdown the pool manager and clean up all containers."""
        logger.info("Shutting down DockerPoolManager")
        self.running = False
        
        if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        
        # Clean up all containers
        with self.pool_lock:
            # Clean up pool containers
            while self.pool:
                pooled_container = self.pool.popleft()
                self._remove_container_from_pool(pooled_container)
            
            # Clean up active containers
            for port, pooled_container in list(self.active_containers.items()):
                self._remove_container_from_pool(pooled_container)
        
        logger.info("DockerPoolManager shutdown complete")


# Legacy GameServerManager for backward compatibility
class GameServerManager:
    def __init__(self, pool_size: int = 3, sim: bool = True):
        self.pool_manager = DockerPoolManager()
        self.pool_size = pool_size
        self.sim = sim

    def allocate_server(self) -> Optional[int]:
        return self.pool_manager.acquire_container("legacy_manager")

    def release_server(self, port: int):
        self.pool_manager.release_container(port, "legacy_manager")

    def shutdown(self):
        self.pool_manager.shutdown()
