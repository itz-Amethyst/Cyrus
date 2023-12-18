"""redis.py"""
from typing import Tuple, Callable, Optional

import redis

from .enums import RedisStatus


def redis_connect(
    host_url: str, local: bool, password: str, port: int
) -> Tuple[RedisStatus, redis.client.Redis]:
    """Attempt to connect to `host_url`. If `local` is set to `True`, it will connect to `cloud` with `password` and return aRedis client instance if successful."""
    connection_method = redis.from_url if local else redis.Redis
    return _connect_generic(connection_method, host_url, password=password, port=port)


def _connect_generic(
    connection_method: Callable, *args, **kwargs
) -> Tuple[RedisStatus, Optional[redis.client.Redis]]:
    try:
        redis_client = connection_method(*args, **kwargs)
    except (redis.AuthenticationError, redis.ConnectionError):
        return RedisStatus.CONN_ERROR, None

    if redis_client.ping():
        return RedisStatus.CONNECTED, redis_client
    return RedisStatus.CONN_ERROR, None
