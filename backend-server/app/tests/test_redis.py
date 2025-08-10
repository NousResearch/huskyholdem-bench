import time
import pytest
from app.service.cache.redis import RedisService


@pytest.fixture(scope="module")
def redis_client():
    # Make sure Redis is running from docker-compose
    client = RedisService(host="redis", port=6379)
    yield client
    # Cleanup keys after test
    client.remove("test_key")
    client.remove("json_key")


def test_put_get_string(redis_client):
    redis_client.put("test_key", "hello")
    assert redis_client.get("test_key") == "hello"


def test_put_get_json(redis_client):
    data = {"foo": "bar", "count": 3}
    redis_client.put("json_key", data)
    result = redis_client.get("json_key")
    assert result == data


def test_expire_key(redis_client):
    redis_client.put("test_key", "expire-me", expire=1)
    time.sleep(2)  # Wait for key to expire
    assert redis_client.get("test_key") is None


def test_remove(redis_client):
    redis_client.put("test_key", "to-be-removed")
    removed = redis_client.remove("test_key")
    assert removed is True
    assert redis_client.get("test_key") is None
