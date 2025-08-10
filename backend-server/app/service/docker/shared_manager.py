import json
import time
import threading
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from enum import Enum
import redis

from app.models.game import GameStatus
from app.service.docker.main import DockerService
from app.service.cache.redis import RedisService
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
    created_by: Optional[str] = None

    def to_dict(self):
        return {
            'port': self.port,
            'container_name': self.container_name,
            'state': self.state.value,
            'acquired_at': self.acquired_at,
            'acquired_by': self.acquired_by,
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            port=data['port'],
            container_name=data['container_name'],
            state=ContainerState(data['state']),
            acquired_at=data.get('acquired_at'),
            acquired_by=data.get('acquired_by'),
            created_by=data.get('created_by')
        )


class SharedDockerPoolManager:
    """
    Docker pool manager that coordinates across multiple workers using Redis.
    """
    
    POOL_KEY = "docker_pool:containers"
    ACTIVE_KEY = "docker_pool:active"
    LOCK_KEY = "docker_pool:lock"
    LOCK_TIMEOUT = 5  # seconds

    SCALING_LOCK_KEY = "docker_pool:scaling_lock"
    SCALING_LOCK_TIMEOUT = 10
    
    def __init__(self):
        self.docker_service = DockerService()
        self.redis_service = RedisService()
        self.redis_client = self.redis_service.client
        self.running = True
        self.sim_mode = True
        
        # Start monitoring thread (only one worker should run this)
        self.should_monitor = self._should_start_monitor()
        if self.should_monitor:
            self.monitor_thread = threading.Thread(target=self._monitor_pool, daemon=True)
            self.monitor_thread.start()
            logger.info("SharedDockerPoolManager: Started pool monitoring thread")
        
        # Initialize pool if needed
        self._ensure_pool_initialized()
        
        logger.info("SharedDockerPoolManager initialized")

    def _should_start_monitor(self) -> bool:
        """Determine if this instance should start the monitoring thread."""
        try:
            # Try to acquire a monitor lock that expires in 60 seconds
            monitor_lock_key = "docker_pool:monitor_lock"
            result = self.redis_client.set(
                monitor_lock_key, 
                "monitoring", 
                ex=60,  # expires in 60 seconds
                nx=True  # only set if not exists
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error checking monitor lock: {e}")
            return False

    def _cleanup_stale_entries(self):
        """Clean up Redis entries for containers that don't actually exist in Docker."""
        try:
            with self._acquire_lock():
                # Get all Docker containers
                actual_containers = self.docker_service.get_all_containers_live_status()
                
                # Check pool containers
                pool_data = self.redis_client.hgetall(self.POOL_KEY)
                stale_pool_ports = []
                
                for port_str, container_data in pool_data.items():
                    container_dict = json.loads(container_data)
                    container_name = container_dict['container_name']
                    
                    if container_name not in actual_containers:
                        logger.warning(f"Removing stale pool entry: {container_name} (port {port_str})")
                        stale_pool_ports.append(port_str)
                
                # Remove stale pool entries
                for port_str in stale_pool_ports:
                    self.redis_client.hdel(self.POOL_KEY, port_str)
                
                # Check active containers
                active_data = self.redis_client.hgetall(self.ACTIVE_KEY)
                stale_active_ports = []
                
                for port_str, container_data in active_data.items():
                    container_dict = json.loads(container_data)
                    container_name = container_dict['container_name']
                    
                    if container_name not in actual_containers:
                        logger.warning(f"Removing stale active entry: {container_name} (port {port_str})")
                        stale_active_ports.append(port_str)
                
                # Remove stale active entries
                for port_str in stale_active_ports:
                    self.redis_client.hdel(self.ACTIVE_KEY, port_str)
                
                # Add existing containers to pool if they're not tracked
                for container_name, status in actual_containers.items():
                    if container_name.startswith("game_server_") and status == "running":
                        # Extract port from container name
                        try:
                            port = int(container_name.split("_")[-1])
                            port_str = str(port)
                            
                            # Check if it's already tracked
                            is_in_pool = self.redis_client.hexists(self.POOL_KEY, port_str)
                            is_in_active = self.redis_client.hexists(self.ACTIVE_KEY, port_str)
                            
                            if not is_in_pool and not is_in_active:
                                logger.info(f"Adding untracked container {container_name} to pool")
                                pooled_container = PooledContainer(
                                    port=port,
                                    container_name=container_name,
                                    state=ContainerState.IDLE,
                                    created_by="pool_cleanup"
                                )
                                self.redis_client.hset(
                                    self.POOL_KEY,
                                    port_str,
                                    json.dumps(pooled_container.to_dict())
                                )
                        except (ValueError, IndexError):
                            logger.warning(f"Could not parse port from container name: {container_name}")
                
                logger.info("Redis cleanup completed")
                
        except Exception as e:
            logger.error(f"Error during Redis cleanup: {e}")

    def _ensure_pool_initialized(self):
        """Ensure the pool is initialized with minimum containers."""
        # First cleanup stale entries
        self._cleanup_stale_entries()
        
        with self._acquire_lock():
            pool_containers = self._get_pool_containers()
            active_containers = self._get_active_containers()
            total_containers = len(pool_containers) + len(active_containers)
            
            if total_containers < settings.DOCKER_POOL_SIZE:
                logger.info(f"Initializing shared pool. Current: {total_containers}, Target: {settings.DOCKER_POOL_SIZE}")
                
                for _ in range(settings.DOCKER_POOL_SIZE - total_containers):
                    if self._add_container_to_pool():
                        logger.info("Added container to shared pool during initialization")
                    else:
                        logger.error("Failed to add container during initialization")
                        break

    def _acquire_lock(self, timeout: int = None):
        """Acquire a distributed lock for pool operations."""
        if timeout is None:
            timeout = self.LOCK_TIMEOUT
            
        class RedisLock:
            def __init__(self, redis_client, key, timeout):
                self.redis_client = redis_client
                self.key = key
                self.timeout = timeout
                self.acquired = False
                
            def __enter__(self):
                end_time = time.time() + self.timeout
                while time.time() < end_time:
                    if self.redis_client.set(self.key, "locked", ex=self.timeout, nx=True):
                        self.acquired = True
                        return self
                    time.sleep(0.1)
                raise Exception(f"Failed to acquire lock {self.key} within {self.timeout} seconds")
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    try:
                        self.redis_client.delete(self.key)
                    except Exception as e:
                        logger.error(f"Error releasing lock {self.key}: {e}")
        
        return RedisLock(self.redis_client, self.LOCK_KEY, timeout)

    def _acquire_scaling_lock(self, timeout: int = None):
        """Acquire lock for scaling operations"""
        if timeout is None:
            timeout = self.SCALING_LOCK_TIMEOUT
        key = self.SCALING_LOCK_KEY
        class ScalingLock:
            def __init__(self, redis_client, key, timeout):
                self.redis_client = redis_client
                self.key = key
                self.timeout = timeout
                self.acquired = False
            
            def __enter__(self):
                end_time = time.time() + self.timeout
                while time.time() < end_time:
                    if self.redis_client.set(self.key, "locked",
                                             ex=self.timeout, nx=True):
                        self.acquired = True
                        return self

                    time.sleep(0.1)
                raise Exception(
                    f"Failed to acquire scaling lock {self.key} within "
                    f"{self.timeout} seconds"
                )
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.acquired:
                    try:
                        self.redis_client.delete(self.key)
                    except Exception as e:
                        logger.error(f"Error releasing scaling lock {self.key}: {e}")

        return ScalingLock(self.redis_client, key, timeout)



    def _get_pool_containers(self) -> List[PooledContainer]:
        """Get all containers in the idle pool."""
        try:
            data = self.redis_client.hgetall(self.POOL_KEY)
            containers = []
            for container_data in data.values():
                container_dict = json.loads(container_data)
                containers.append(PooledContainer.from_dict(container_dict))
            return containers
        except Exception as e:
            logger.error(f"Error getting pool containers: {e}")
            return []

    def _get_active_containers(self) -> List[PooledContainer]:
        """Get all active (acquired) containers."""
        try:
            data = self.redis_client.hgetall(self.ACTIVE_KEY)
            containers = []
            for container_data in data.values():
                container_dict = json.loads(container_data)
                containers.append(PooledContainer.from_dict(container_dict))
            return containers
        except Exception as e:
            logger.error(f"Error getting active containers: {e}")
            return []

    def _add_container_to_pool(self) -> bool:
        """Add a new container to the shared pool."""
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
                state=ContainerState.IDLE,
                created_by=f"worker_{threading.current_thread().ident}"
            )
            
            # Add to Redis pool
            self.redis_client.hset(
                self.POOL_KEY, 
                str(port), 
                json.dumps(pooled_container.to_dict())
            )
            
            logger.info(f"Added idle container {container_name} (port {port}) to shared pool")
            return True
            
        except Exception as e:
            logger.error(f"Error adding container to shared pool: {e}")
            return False

    def acquire_container(self, worker_id: str, timeout: int = None) -> Optional[int]:
        """Acquire a container from the shared pool."""
        if timeout is None:
            timeout = settings.DOCKER_CONTAINER_ACQUISITION_TIMEOUT
        
        start_time = time.time()
        retries = 0
        
        while time.time() - start_time < timeout and retries < settings.DOCKER_POOL_MAX_RETRIES:
            try:
                with self._acquire_lock():
                    # Get available containers
                    pool_data = self.redis_client.hgetall(self.POOL_KEY)
                    
                    if pool_data:
                        # Get the first available container
                        port_str, container_data = next(iter(pool_data.items()))
                        port = int(port_str)
                        container_dict = json.loads(container_data)
                        pooled_container = PooledContainer.from_dict(container_dict)
                        
                        # Move from pool to active
                        self.redis_client.hdel(self.POOL_KEY, port_str)
                        
                        # Update container state
                        pooled_container.state = ContainerState.ACQUIRED
                        pooled_container.acquired_at = time.time()
                        pooled_container.acquired_by = worker_id
                        
                        # Add to active containers
                        self.redis_client.hset(
                            self.ACTIVE_KEY,
                            str(port),
                            json.dumps(pooled_container.to_dict())
                        )
                        
                        logger.info(f"Container {pooled_container.container_name} (port {port}) "
                                  f"acquired by worker {worker_id}")
                        return port
                    
                    # No containers available - check if we should create one or wait
                    pool_containers = self._get_pool_containers()
                    active_containers = self._get_active_containers()
                    total_containers = len(pool_containers) + len(active_containers)
                    
                    # Only create new containers if we have fewer than the target pool size
                    # This prevents creating containers when all are just temporarily busy
                    if total_containers < settings.DOCKER_POOL_SIZE:
                        logger.info(f"Pool has {total_containers} containers, target is {settings.DOCKER_POOL_SIZE}, creating new container")
                        if self._add_container_to_pool():
                            continue
                        else:
                            logger.error("Failed to create new container")
                    else:
                        logger.info(f"All {total_containers} containers are busy, waiting for one to be released...")
                
            except Exception as e:
                logger.error(f"Error acquiring container: {e}")
            
            # Wait before retrying - containers should be released soon
            time.sleep(2)  # Increased wait time to reduce spinning
            retries += 1
        
        logger.warning(f"Worker {worker_id} failed to acquire container after {retries} retries and {timeout}s timeout")
        return None

    def release_container(self, port: int, worker_id: str, cleanup: bool = True) -> bool:
        """Release a container back to the shared pool."""
        try:
            with self._acquire_lock():
                # Get container from active list
                container_data = self.redis_client.hget(self.ACTIVE_KEY, str(port))
                if not container_data:
                    logger.warning(f"Container on port {port} not found in active containers")
                    return False
                
                container_dict = json.loads(container_data)
                pooled_container = PooledContainer.from_dict(container_dict)
                
                # Verify ownership
                if pooled_container.acquired_by != worker_id:
                    logger.warning(f"Worker {worker_id} trying to release container owned by {pooled_container.acquired_by}")
                    return False
                
                # Remove from active containers
                self.redis_client.hdel(self.ACTIVE_KEY, str(port))
                
                try:
                    if cleanup:
                        # Clean the container
                        self.docker_service.clean_container_internal(pooled_container.container_name)
                    
                    # Reset container state
                    pooled_container.state = ContainerState.IDLE
                    pooled_container.acquired_at = None
                    pooled_container.acquired_by = None
                    
                    # Return to pool
                    self.redis_client.hset(
                        self.POOL_KEY,
                        str(port),
                        json.dumps(pooled_container.to_dict())
                    )
                    
                    logger.info(f"Container {pooled_container.container_name} (port {port}) "
                              f"released by worker {worker_id} and returned to shared pool")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error cleaning/releasing container on port {port}: {e}")
                    # If cleanup failed, remove the container entirely
                    self._remove_container_from_pool(pooled_container)
                    return False
                    
        except Exception as e:
            logger.error(f"Error releasing container: {e}")
            return False

    def _remove_container_from_pool(self, pooled_container: PooledContainer):
        """Remove a container from the pool and clean up resources."""
        try:
            self.docker_service.stop_and_remove_container(pooled_container.container_name)
            self.docker_service.release_port(pooled_container.port)
            
            # Remove from Redis (both pool and active, just in case)
            self.redis_client.hdel(self.POOL_KEY, str(pooled_container.port))
            self.redis_client.hdel(self.ACTIVE_KEY, str(pooled_container.port))
            
            logger.info(f"Removed container {pooled_container.container_name} from shared pool")
        except Exception as e:
            logger.error(f"Error removing container {pooled_container.container_name}: {e}")

    def get_pool_status(self) -> Dict:
        """Get current status of the shared container pool."""
        try:
            pool_containers = self._get_pool_containers()
            active_containers = self._get_active_containers()
            
            return {
                "pool_size": len(pool_containers),
                "active_containers": len(active_containers),
                "total_containers": len(pool_containers) + len(active_containers),
                "target_pool_size": settings.DOCKER_POOL_SIZE,
                "idle_containers": len([c for c in pool_containers if c.state == ContainerState.IDLE]),
                "acquired_containers": len([c for c in active_containers if c.state == ContainerState.ACQUIRED]),
                "shared_pool": True
            }
        except Exception as e:
            logger.error(f"Error getting pool status: {e}")
            return {"error": str(e)}

    def _monitor_pool(self):
        """Monitor and maintain the shared container pool."""
        while self.running:
            try:
                # Refresh monitor lock
                monitor_lock_key = "docker_pool:monitor_lock"
                self.redis_client.expire(monitor_lock_key, 60)
                
                with self._acquire_lock(timeout=10):
                    pool_containers = self._get_pool_containers()
                    active_containers = self._get_active_containers()
                    
                    # Ensure minimum pool size
                    total_needed = settings.DOCKER_POOL_SIZE - len(pool_containers) - len(active_containers)
                    if total_needed > 0:
                        logger.info(f"Pool below target size, adding {total_needed} containers")
                        for _ in range(total_needed):
                            if not self._add_container_to_pool():
                                logger.error("Failed to add container during monitoring")
                                break
                    
                    # Prune excess containers
                    excess = len(pool_containers) - (settings.DOCKER_POOL_SIZE + 2)
                    if excess > 0:
                        logger.info(f"Pool has excess containers, removing {excess}")
                        for i in range(excess):
                            if pool_containers:
                                container = pool_containers.pop()
                                self._remove_container_from_pool(container)
                    
                    # Check for stale acquired containers
                    current_time = time.time()
                    stale_containers = []
                    for container in active_containers:
                        if (container.acquired_at and 
                            current_time - container.acquired_at > settings.GAME_RUN_TIMEOUT + 60):
                            logger.warning(f"Container on port {container.port} appears to be stale, removing")
                            stale_containers.append(container)
                    
                    for container in stale_containers:
                        self._remove_container_from_pool(container)
                
                time.sleep(settings.DOCKER_POOL_MONITOR_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in shared pool monitoring: {e}")
                time.sleep(10)

    def shutdown(self):
        """Shutdown the shared pool manager."""
        logger.info("Shutting down SharedDockerPoolManager")
        self.running = False
        
        try:
            with self._acquire_lock(timeout=10):
                # Clean up all containers
                pool_containers = self._get_pool_containers()
                active_containers = self._get_active_containers()
                
                for container in pool_containers + active_containers:
                    self._remove_container_from_pool(container)
                
                # Clear Redis keys
                self.redis_client.delete(self.POOL_KEY)
                self.redis_client.delete(self.ACTIVE_KEY)
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("SharedDockerPoolManager shutdown complete") 