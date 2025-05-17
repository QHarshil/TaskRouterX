import redis.asyncio as redis
import os
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv()

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_DLQ_KEY = os.getenv("REDIS_DLQ_KEY", "taskrouterx:dlq")

# Configure logger
logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache helper for TaskRouterX.
    Provides methods for caching, retrieving, and managing task data in Redis.
    """

    def __init__(self):
        self.redis = None
        self.connected = False

    async def connect(self):
        """
        Connect to Redis server.
        """
        if not self.connected:
            try:
                self.redis = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
                self.connected = True
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def disconnect(self):
        """
        Disconnect from Redis server.
        """
        if self.connected and self.redis:
            await self.redis.close()
            self.connected = False
            logger.info("Disconnected from Redis")

    async def set(self, key, value, expiry=None):
        """
        Set a key-value pair in Redis.
        
        Args:
            key (str): The key to set
            value (Any): The value to set (will be JSON serialized)
            expiry (int, optional): Expiry time in seconds
        """
        if not self.connected:
            await self.connect()
        
        try:
            serialized_value = json.dumps(value)
            if expiry:
                await self.redis.setex(key, expiry, serialized_value)
            else:
                await self.redis.set(key, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    async def get(self, key):
        """
        Get a value from Redis by key.
        
        Args:
            key (str): The key to retrieve
            
        Returns:
            Any: The deserialized value or None if key doesn't exist
        """
        if not self.connected:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    async def delete(self, key):
        """
        Delete a key from Redis.
        
        Args:
            key (str): The key to delete
        """
        if not self.connected:
            await self.connect()
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    async def add_to_dlq(self, task_data, error_info):
        """
        Add a failed task to the Dead Letter Queue.
        
        Args:
            task_data (dict): The task data that failed processing
            error_info (str): Information about the error
        """
        if not self.connected:
            await self.connect()
        
        try:
            dlq_entry = {
                "task_data": task_data,
                "error_info": error_info,
                "timestamp": json.dumps({"$date": {"$numberLong": str(int(time.time() * 1000))}})
            }
            await self.redis.lpush(REDIS_DLQ_KEY, json.dumps(dlq_entry))
            logger.info(f"Added task {task_data.get('id', 'unknown')} to DLQ")
            return True
        except Exception as e:
            logger.error(f"Failed to add task to DLQ: {e}")
            return False

    async def get_dlq_entries(self, count=10):
        """
        Get entries from the Dead Letter Queue.
        
        Args:
            count (int): Maximum number of entries to retrieve
            
        Returns:
            list: List of DLQ entries
        """
        if not self.connected:
            await self.connect()
        
        try:
            entries = await self.redis.lrange(REDIS_DLQ_KEY, 0, count - 1)
            return [json.loads(entry) for entry in entries]
        except Exception as e:
            logger.error(f"Failed to get DLQ entries: {e}")
            return []

    async def retry_dlq_entry(self, index):
        """
        Remove an entry from the DLQ for retry.
        
        Args:
            index (int): Index of the entry to retry
            
        Returns:
            dict: The removed entry or None if failed
        """
        if not self.connected:
            await self.connect()
        
        try:
            # Get the entry
            entry = await self.redis.lindex(REDIS_DLQ_KEY, index)
            if not entry:
                return None
                
            # Remove it from the DLQ
            await self.redis.lrem(REDIS_DLQ_KEY, 1, entry)
            
            return json.loads(entry)
        except Exception as e:
            logger.error(f"Failed to retry DLQ entry: {e}")
            return None


# Create a singleton instance
cache = RedisCache()
