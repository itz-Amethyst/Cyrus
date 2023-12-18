"""cache.py"""
import asyncio
import json
from datetime import timedelta
from functools import partial , wraps , update_wrapper
from http import HTTPStatus
from typing import Union

from fastapi import Response

from .client import Cyrus
from .util import (
    deserialize_json,
    ONE_DAY_IN_SECONDS,
    ONE_HOUR_IN_SECONDS,
    ONE_MONTH_IN_SECONDS,
    ONE_WEEK_IN_SECONDS,
    ONE_YEAR_IN_SECONDS,
    serialize_json,
)


def cache(*, expire: Union[int, timedelta] = ONE_YEAR_IN_SECONDS):
    """Enable caching behavior for the decorated function.

    Args:
        expire (Union[int, timedelta], optional): The number of seconds
            from now when the cached response should expire. Defaults to 31,536,000
            seconds (i.e., the number of seconds in one year).
    """

    def outer_wrapper(func):
        @wraps(func)
        async def inner_wrapper(*args, **kwargs):
            """Return cached value if one exists, otherwise evaluate the wrapped function and cache the result."""

            func_kwargs = kwargs.copy()
            request = func_kwargs.pop("request", None)
            response = func_kwargs.pop("response", None)
            create_response_directly = not response
            if create_response_directly:
                response = Response()
            redis_cache = Cyrus()

            if redis_cache.not_connected or redis_cache.request_is_not_cacheable(
                request
            ):
                # If the redis client is not connected or the request is not cacheable, no caching behavior is performed.
                return await get_api_response_async(func, *args, **kwargs)

            key = redis_cache.get_cache_key(func, *args, **kwargs)
            ttl, in_cache = redis_cache.check_cache(key)

            if in_cache:
                redis_cache.set_response_headers(
                    response, True, deserialize_json(in_cache), ttl
                )
                if redis_cache.requested_resource_not_modified(request, in_cache):
                    response.status_code = int(HTTPStatus.NOT_MODIFIED)
                    return create_response(response, None, create_response_directly)

                # Convert bytes key to json
                # converted_json_data = json.loads(in_cache)
                # converted_json_data = converted_json_data[key] if key in converted_json_data else converted_json_data

                converted_json_data = json.loads(in_cache).get(key , json.loads(in_cache))

                return create_response(response, str(converted_json_data), create_response_directly)

            response_data = await get_api_response_async(func, *args, **kwargs)
            ttl = calculate_ttl(expire)
            cached, serialized_dict = redis_cache.add_to_cache(key, response_data, ttl)

            if cached:
                redis_cache.set_response_headers(
                    response, cache_hit=False, response_data=response_data, ttl=ttl
                )
                if hasattr(response_data, "__len__"):
                    return create_response(
                        response, serialize_json(response_data), create_response_directly
                    )
                else:
                    return create_response(
                        response , serialized_dict[key][0] , create_response_directly
                    )

            return response_data

        return inner_wrapper

    return outer_wrapper


async def get_api_response_async(func, *args, **kwargs):
    """Helper function that allows decorator to work with both async and non-async functions."""
    return (
        await func(*args, **kwargs)
        if asyncio.iscoroutinefunction(func)
        else func(*args, **kwargs)
    )


def calculate_ttl(expire: Union[int, timedelta]) -> int:
    """Converts expire time to total seconds and ensures that ttl is capped at one year."""
    if isinstance(expire, timedelta):
        expire = int(expire.total_seconds())
    return min(expire, ONE_YEAR_IN_SECONDS)


def create_response(response, content, create_directly):
    """Creates a FastAPI response."""
    if create_directly:
        return Response(
            content = content ,
            media_type = "application/json" ,
            headers = {"Content-Length": str(len(content))} ,
            status_code = response.status_code ,
        )
    return content


# Combine 2 funcs into 1
cache_one_minute = partial(cache, expire=60)
cache_one_hour = partial(cache, expire=ONE_HOUR_IN_SECONDS)
cache_one_day = partial(cache, expire=ONE_DAY_IN_SECONDS)
cache_one_week = partial(cache, expire=ONE_WEEK_IN_SECONDS)
cache_one_month = partial(cache, expire=ONE_MONTH_IN_SECONDS)
cache_one_year = partial(cache, expire=ONE_YEAR_IN_SECONDS)


for cache_wrapper in [
    cache_one_minute,
    cache_one_hour,
    cache_one_day,
    cache_one_week,
    cache_one_month,
    cache_one_year,
]:
    wraps(cache_wrapper)(cache)

# update_wrapper(cache_one_minute, cache)
# update_wrapper(cache_one_hour, cache)
# update_wrapper(cache_one_day, cache)
# update_wrapper(cache_one_week, cache)
# update_wrapper(cache_one_month, cache)
# update_wrapper(cache_one_year, cache)