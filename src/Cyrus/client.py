import json
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple, Type, Union

from fastapi import Request, Response
from redis import client
from sqlalchemy.orm import registry

from .enums import RedisEvent, RedisStatus
from .key_gen import get_cache_key
from .redis import redis_connect
from .util import serialize_json

DEFAULT_RESPONSE_HEADER = "X-FastAPI-Cache"
ALLOWED_HTTP_TYPES = ["GET"]
LOG_TIMESTAMP = "%m/%d/%Y %I:%M:%S %p"
HTTP_TIME = "%a, %d %b %Y %H:%M:%S GMT"

# Default Logging_system
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MetaSingleton(type):
    """Metaclass for creating classes that allow only a single instance to be created."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Cyrus(metaclass=MetaSingleton):
    """Communicates with Redis server to cache API response data."""

    host_url: str
    prefix: str = None
    response_header: str = None
    status: RedisStatus = RedisStatus.NONE
    redis: client.Redis = None
    logger_system: logging.Logger = None
    local: bool = False
    password: str = None
    port: int = 0

    @property
    def connected(self):
        return self.status == RedisStatus.CONNECTED

    @property
    def not_connected(self):
        return not self.connected

    def __init__(
        self,
        prefix: Optional[str] = None,
        response_header: Optional[str] = None,
        ignore_arg_types: Optional[List[Type[object]]] = None,
        logger_system: Optional[logging.Logger] = None,
        local: Optional[bool] = False,
        host_url: str = "localhost",
        password: Optional[str] = None,
        port: Optional[int] = 0,
    ) -> None:
        """Initialize the redis system you can `config` the essential settings.
        Args:
             prefix (str, optional): Prefix to add to every cache key stored in the
                 Redis database. Defaults to None.
             response_header (str, optional): Name of the custom header field used to
                 identify cache hits/misses. Defaults to None.
             ignore_arg_types (List[Type[object]], optional): Each argument to the
                 API endpoint function is used to compose the cache key. If there
                 are any arguments that have no effect on the response (such as a
                 `Request` or `Response` object), including their type in this list
                 will ignore those arguments when the key is created. Defaults to None.
             logger_system (logging.Logger, optional): Gets your custom logging config system
                 if you provided for log operation, if not uses the default one
             local (bool, optional): Set to True if you use local redis server.
             host_url (str): URL for a Redis database.
             password (str, optional): Password for Redis Cloud.
             port (int, optional): Port number for Redis Cloud.
        """
        self.prefix = prefix
        self.response_header = response_header or DEFAULT_RESPONSE_HEADER
        self.ignore_arg_types = ignore_arg_types
        self.logger_system = logger_system or logger
        self.local = local
        self.host_url = host_url
        self.password = password
        self.port = port

        self._connect()

    def _connect(self):
        self.log(
            RedisEvent.CONNECT_BEGIN, msg="Attempting to connect to Redis server..."
        )
        self.status, self.redis = redis_connect(
            self.host_url, self.local, self.password, self.port
        )
        if self.status == RedisStatus.CONNECTED:
            self.log(
                RedisEvent.CONNECT_SUCCESS, msg="Redis client is connected to server."
            )
        if self.status == RedisStatus.AUTH_ERROR:  # pragma: no cover
            self.log(
                RedisEvent.CONNECT_FAIL,
                msg="Unable to connect to redis server due to authentication error.",
            )
        if self.status == RedisStatus.CONN_ERROR:  # pragma: no cover
            self.log(
                RedisEvent.CONNECT_FAIL,
                msg="Redis server did not respond to PING message.",
            )

    def get_cache_key(self, func: Callable, *args: List, **kwargs: Dict) -> str:
        return get_cache_key(self.prefix, self.ignore_arg_types, func, *args, **kwargs)

    def check_cache(self, key: str) -> Tuple[int, str]:
        pipe = self.redis.pipeline()
        ttl, in_cache = pipe.ttl(key).get(key).execute()
        if in_cache:
            self.log(RedisEvent.KEY_FOUND_IN_CACHE, key=key)
        return ttl, in_cache

    def requested_resource_not_modified(
        self, request: Request, cached_data: str
    ) -> bool:
        if not request or "If-None-Match" not in request.headers:
            return False
        check_etags = [
            etag.strip() for etag in request.headers["If-None-Match"].split(",") if etag
        ]
        if len(check_etags) == 1 and check_etags[0] == "*":
            return True
        return self.get_etag(cached_data) in check_etags

    def filter_attributes( obj ):
        excluded_types = (datetime , dict, registry, datetime)  # Add other types you want to exclude
        return {key: value for key , value in obj.__dict__.items() if not isinstance(value , excluded_types)}

    def add_to_cache(self, key: str, value: Dict, expire: int) -> bool:
        try:
            if hasattr(value , "__len__"):
                serialized_messages = [serialize_json(obj.__dict__) for obj in value]
            else:
                serialized_messages = [serialize_json(value.__dict__)]
            serialized_dict = {key: serialized_messages} if serialized_messages else {}
        except TypeError as e:
            message = f"Object of type {type(value)} is not JSON-serializable: => str{e}"
            self.log(RedisEvent.FAILED_TO_CACHE_KEY, msg=message, key=key)
            return False
        cached = self.redis.set(name=key, value=json.dumps(serialized_dict), ex=expire)
        if cached:
            self.log(RedisEvent.KEY_ADDED_TO_CACHE, key=key)
        else:
            self.log(RedisEvent.FAILED_TO_CACHE_KEY, key=key, value=value)
        return cached , serialized_dict

    def set_response_headers(
        self,
        response: Response,
        cache_hit: bool,
        response_data: Dict = None,
        ttl: int = None,
    ) -> None:
        response.headers[self.response_header] = "Hit" if cache_hit else "Miss"
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        response.headers["Expires"] = expires_at.strftime(HTTP_TIME)
        response.headers["Cache-Control"] = f"max-age={ttl}"
        # test, cached_data = self.get_etag(response_data)
        # response.headers["ETag"] = test
        # if "last_modified" in cached_data:  # pragma: no cover
        #     response.headers["Last-Modified"] = response_data["last_modified"]

    def log(
        self,
        event: RedisEvent,
        msg: Optional[str] = None,
        key: Optional[str] = None,
        value: Optional[str] = None,
    ):
        """Log `RedisEvent` using the configured `Logger` object"""
        message = f"{self.get_log_time()} | {event.name}"
        if msg:
            message += f": {msg}"
        if key:
            message += f": key={key}"
        if value:
            message += f", value={value}"
        logger.info(message)

    #? Rebuild Required
    # @staticmethod
    # def get_etag(cached_data: Union[str, bytes, Dict]) -> str:
    #
    #     if isinstance(cached_data, bytes):
    #         cached_data = cached_data.decode()
    #
    #     if hasattr(cached_data, "__len__"):
    #
    #         for obj in cached_data:
    #             serialized_messages = []
    #             # filtered_value = self.filter_attributes(obj.__dict__)
    #             serialized_object = serialize_json(obj.__dict__)
    #             # serialized_messages.append(serialized_object)
    #             serialized_messages.append(serialized_object)
    #
    #
    #         return f"W/{hash(tuple(serialized_messages))}", serialized_messages
    #
    #     if isinstance(cached_data.__dict__, dict):
    #         cached_data = serialize_json(cached_data.__dict__)
    #     return f"W/{hash(cached_data)}" , cached_data

    @staticmethod
    def get_log_time():
        """Get a timestamp to include with a log message."""
        return datetime.now().strftime(LOG_TIMESTAMP)

    @staticmethod
    def request_is_not_cacheable(request: Request) -> bool:
        return request and (
            request.method not in ALLOWED_HTTP_TYPES
            or any(
                directive in request.headers.get("Cache-Control", "")
                for directive in ["no-store", "no-cache"]
            )
        )
