
<p class="align-center" style="font-weight: bold">
  ⏱️ Cyrus: Simplifying Caching in FastAPI. 📃
</p>

<p align="center">
  <img src="https://media.discordapp.net/attachments/921633563810627588/1186359324709228575/cyrus_1.jpg?ex=6592f638&is=65808138&hm=fef999c02bee2306eebea241d55aae1a2640f543b77c240ac8fe911d577e120c&=&format=webp&width=723&height=416" alt="Cyrus"/>
</p>

------

## Cyrus

[![PyPI version](https://badge.fury.io/py/Cyrus-kit.svg)](https://badge.fury.io/py/Cyrus-kit)
![PyPI - Downloads](https://img.shields.io/pypi/dm/Cyrus-kit?color=%234DC71F)
![PyPI - License](https://img.shields.io/pypi/l/Cyrus-kit?color=%25234DC71F)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/Cyrus-kit)

------

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Initialize Redis](#initialize-redis)
  - [`@cache` Decorator](#cache-decorator)
    - [Pre-defined Lifetimes](#pre-defined-lifetimes)
  - [Cache Keys](#cache-keys)
  - [Multiple Objects Caching](#multiple-objects-caching)
- [Last Word](#last-word)

## Features

**Data Caching:**
- Cache response data for async and non-async path operation functions.operation functions.
- Tailor the lifespan of cached data for each API endpoint with ease.

**Cache Management:**
- Dynamically handle requests with `Cache-Control` headers containing `no-cache` or `no-store`, ensuring precise control over caching behavior.
- Streamline responses for requests with `If-None-Match` headers, providing a status of `304 NOT MODIFIED` when the `ETag` for the requested resource matches the header value.


## Installation

`pip install Cyrus-Kit`

## Usage

### Initialize Redis

#### Step 1: Create an Instance

Create a `Cyrus` instance when your application starts by [defining an event handler for the `"startup"` event](https://fastapi.tiangolo.com/advanced/events/) as shown below:

```python {linenos=table}
import logging
from fastapi import FastAPI , Request , Response
from Cyrus import Cyrus
from sqlalchemy.orm import Session

# Your logger config if you have otherwise no need (default)
logger_system = logging.getLogger(__name__)

REDIS_URL = "redis-1523.c291.ap-northeast-1-2.ec2.cloud.redislabs.com"
REDIS_PASSWORD = "1234"
REDIS_PORT = 1492

app = FastAPI(title = "FastAPI Redis Cache Example")


@app.on_event("startup")
def startup():
  redis_cache = Cyrus(
    logger_system = logger_system ,
    host_url = REDIS_URL ,
    port = REDIS_PORT ,
    password = REDIS_PASSWORD ,
    prefix = "myapi-cache" ,
    response_header = "X-MyAPI-Cache" ,
    ignore_arg_types = [Request , Response , Session]
  )
```

After creating the instance, the only required argument for this method is the URL for the Redis database (`host_url`). All other arguments are optional:

- `host_url` (`str`) &mdash; Redis database URL. (_**Required**_)
- `prefix` (`str`) &mdash; Prefix to add to every cache key stored in the Redis database. (_Optional_, defaults to `None`)
- `response_header` (`str`) &mdash; Name of the custom header field used to identify cache hits/misses. (_Optional_, defaults to `X-FastAPI-Cache`)
- `ignore_arg_types` (`List[Type[object]]`) &mdash; Cache keys are created (in part) by combining the name and value of each argument used to invoke a path operation function. If any of the arguments have no effect on the response (such as a `Request` or `Response` object), including their type in this list will ignore those arguments when the key is created. (_Optional_, defaults to `[Request, Response]`)
  - The example shown here includes the `sqlalchemy.orm.Session` type, if your project uses SQLAlchemy as a dependency ([as demonstrated in the FastAPI docs](https://fastapi.tiangolo.com/tutorial/sql-databases/)), you should include `Session` in `ignore_arg_types` in order for cache keys to be created correctly.

- `logger_system` (`logging.Logger`) &mdash; Gets your custom logging config system if you provided for log operation, if not uses the default one.
- `local` (`bool`) &mdash; Set this to `True` if you use local redis server(Optional, defaults to `False`).
- `password` (`str`) &mdash; Password for Redis Cloud (Optional, defaults to `None`).
- `port` (`int`) &mdash; Port number for Redis Cloud (Optional, defaults to `0`).

### `@cache` Decorator

Decorating a path function with `@cache` enables caching for the endpoint. **Response data is only cached for `GET` operations**, If no arguments are provided, responses will be set to expire after one year.

```python
# WILL NOT be cached
@app.get("/no_cache")
def get_data():
    return Response(status_code = 200, content = "Data will not be Cached!")

# Will be cached for one year
@app.get("/cached_data")
@cache()
async def get_cached_data():
    return Response(status_code = 200, content = "This Data cached for 1 year!")
```

Response data for the API endpoint at `/cached_data` will be cached by the Redis server. Log messages are written to console with logger system you provided or default one:

```console
18:53:02.081: |<INFO>| [client]: 12/16/2023 06:53:02 PM | CONNECT_BEGIN: Attempting to connect to Redis server...
18:53:04.343: |<INFO>| [client]: 12/16/2023 06:53:04 PM | CONNECT_SUCCESS: Redis client is connected to server.
18:53:10.523: |<INFO>| [client]: 12/16/2023 06:53:10 PM | KEY_ADDED_TO_CACHE: key=api.get_cached_data().
18:53:12.103: |<INFO>| [client]: 12/16/2023 06:53:12 PM | KEY_FOUND_IN_CACHE: key=api.get_cached_data().
```

The log messages indicate two successful **`200 OK`** responses for the same request (**`GET /cached_data`**). 

- The first request executed the `get_cached_data` function, storing the result in Redis under the key `api.get_cached_data()`. 
- The second request, however, did not execute the `get_cached_data` function. Instead, it retrieved the cached result and served it as the response.

In typical scenarios, response data should expire much sooner than one year. You can use the `expire` parameter to specify the number of seconds before the data is automatically deleted.

```python
# Will be cached for thirty seconds
@app.get("/dynamic_data")
@cache(expire=30)
def get_dynamic_data(request: Request, response: Response):
    return {"success": True, "message": "this data should only be cached temporarily"}
```

> **NOTE!** `expire` can be either an `int` value or `timedelta` object. When the TTL is very short (like the example above) this results in a decorator that is expressive and requires minimal effort to parse visually. For durations an hour or longer (e.g., `@cache(expire=86400)`), IMHO, using a `timedelta` object is much easier to grok (`@cache(expire=timedelta(days=1))`).


#### Pre-defined Lifetimes

The decorators listed below define several common durations and can be used in place of the `@cache` decorator:

- `@cache_one_minute`
- `@cache_one_hour`
- `@cache_one_day`
- `@cache_one_week`
- `@cache_one_month`
- `@cache_one_year`

For example, instead of `@cache(expire=timedelta(days=1))`, you could use:

```python
from Cyrus import cache_one_day

@router.get("/{id}", response_model = schemas.PostView)
@cache_one_day()
def get_post_by_id(id:int, db: Session = Depends(get_db)):
  
    post = db.query(Post).get(id)
    
    if not post:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"post with this id: {id} was not found")
    return post
```

### Cache Keys

Consider the `/get_user` API route defined below. This is the first path function we have seen where the response depends on the value of an argument (`id: int`). This is a typical CRUD operation where `id` is used to retrieve a `User` record from a database. The API route also includes a dependency that injects a `Session` object (`db`) into the function, [per the instructions from the FastAPI docs](https://fastapi.tiangolo.com/tutorial/sql-databases/#create-a-dependency):

```python
@router.get('/{id}', response_model = schemas.UserView)
def get_user(id: str, db: Session = Depends(get_db)):
    user = db.query(User).get(id)
    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"User with this id {id} does not exists")
    return user
```

#### Log Messages:
You can figure out what is happening in the log messages below:

```console
INFO:uvicorn.error:Application startup complete.
18:04:19.690 |<INFO>| [client]: 12/18/2023 06:04:19 PM | KEY_ADDED_TO_CACHE: key=myapi-cache:app.routers.user.get_user(id=XOM-vquaelshNVXS)
18:04:25.120 |<INFO>| [client]: 12/18/2023 06:04:25 PM | KEY_FOUND_IN_CACHE: key=myapi-cache:app.routers.user.get_user(id=XOM-vquaelshNVXS)
```

Now, every request for the same `id` generates the same key value (`myapi-cache:app.routers.get_user(id=XOM-vquaelshNVXS)`). As expected, the first request adds the key/value pair to the cache, and each subsequent request retrieves the value from the cache based on the key.

### Multiple Objects Caching

Here is an endpoint from one of my projects:

```python
from Cyrus import cache_one_week

@router.get('/get_all_posts')
@cache_one_week
def get_all_posts(db: Session = Depends(get_db)):
    return  db.query(Post).all()
```
- **1** - The `cache_one_week` decorator is applied to the `get_all_posts` route.
- **2** - The `get_all_posts` route fetches all posts from the `database` using SQLAlchemy.

Here you can find more information:

```console
INFO:uvicorn.error:Application startup complete.
18:12:13.690 |<INFO>| [client]: 12/18/2023 06:12:13 PM | KEY_ADDED_TO_CACHE: key=myapi-cache:app.routers.post.get_all_posts()
18:12:39.120 |<INFO>| [client]: 12/18/2023 06:12:39 PM | KEY_FOUND_IN_CACHE: key=myapi-cache:app.routers.post.get_all_posts()
```

> **NOTE!** The current implementation is `not optimal` for handling `multiple` return datasets. There are known issues and potential `bugs` in the existing code. `Contributions` and suggestions for `improvement` are highly encouraged! Feel free to contribute to make it better and more robust. Your input can help enhance the functionality.


### Last Word
🏆
Thank you for exploring our package! Your feedback, bug reports, and contributions are highly valued. If you encounter issues or have ideas for improvements, please open an issue or submit a pull request. Let's build and enhance this package together! 🚀
