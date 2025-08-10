import redis
import json
from redis.exceptions import RedisError
from app.config.setting import settings


class RedisService:
    def __init__(self, host=None, port=6379, db=0):
        # Use settings if no host specified
        if host is None:
            host = settings.REDIS_URL
            
        try:
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            # Test connection
            self.client.ping()
        except RedisError as e:
            raise ConnectionError(f"Redis connection failed: {e}")

    def put(self, key, value, expire=None):
        """
        Store a key-value pair in Redis with optional expiration time.
        Automatically serializes dicts/lists to JSON.
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            if expire:
                self.client.setex(key, expire, value)
            else:
                self.client.set(key, value)
        except RedisError as e:
            print(f"Redis put error for key '{key}': {e}")

    def get(self, key):
        """
        Retrieve the value associated with a key from Redis.
        Automatically deserializes JSON if possible.
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except RedisError as e:
            print(f"Redis get error for key '{key}': {e}")
            return None

    def remove(self, key):
        """
        Remove a key-value pair from Redis.
        Returns True if a key was deleted, False otherwise.
        """
        try:
            return self.client.delete(key) > 0
        except RedisError as e:
            print(f"Redis remove error for key '{key}': {e}")
            return False

    def store_tarstream(self, username: str, tarstream_bytes: bytes, expire=None):
        """
        Store a tarstream (containing player.py and requirements.txt) in Redis cache.
        Replaces any existing cache for the given username.
        
        Args:
            username (str): The username to use as cache key
            tarstream_bytes (bytes): The tarstream bytes (created using create_tar_from_files)
            expire (int, optional): Expiration time in seconds
        
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            # Store in Redis with username as key
            cache_key = f"tarstream:{username}"
            
            if expire:
                self.client.setex(cache_key, expire, tarstream_bytes)
            else:
                self.client.set(cache_key, tarstream_bytes)
            
            return True
            
        except Exception as e:
            print(f"Redis store_tarstream error for username '{username}': {e}")
            return False

    def get_tarstream(self, username: str):
        """
        Retrieve the cached tarstream for a given username.
        
        Args:
            username (str): The username to retrieve cache for
            
        Returns:
            bytes: The tarstream bytes if found, None otherwise
        """
        try:
            cache_key = f"tarstream:{username}"
            tarstream_bytes = self.client.get(cache_key)
            
            if tarstream_bytes is None:
                return None

            # Redis decode_responses=True converts bytes to string, so we need to handle this
            if isinstance(tarstream_bytes, str):
                # If it's a string, it was decoded - we need the raw bytes
                # Re-fetch without decode_responses
                raw_client = redis.Redis(
                    host=self.client.connection_pool.connection_kwargs['host'],
                    port=self.client.connection_pool.connection_kwargs['port'],
                    db=self.client.connection_pool.connection_kwargs['db'],
                    decode_responses=False
                )
                tarstream_bytes = raw_client.get(cache_key)
            
            return tarstream_bytes
            
        except RedisError as e:
            print(f"Redis get_tarstream error for username '{username}': {e}")
            return None

    def flush_all_tarstreams(self):
        """
        Remove all cached tarstreams from Redis.
        
        Returns:
            int: Number of tarstream keys deleted
        """
        try:
            # Find all tarstream keys
            tarstream_keys = self.client.keys("tarstream:*")
            
            if not tarstream_keys:
                return 0
                
            # Delete all tarstream keys
            deleted_count = self.client.delete(*tarstream_keys)
            return deleted_count
            
        except RedisError as e:
            print(f"Redis flush_all_tarstreams error: {e}")
            return 0
