# poet-api

Requests with Limiter.

Uses [`create_sqlite_limiter`](https://github.com/vutran1710/PyrateLimiter/blob/8cb467ea54c68368eaf34deef1a6cc38c41218a2/pyrate_limiter/limiter_factory.py#L55) from [pyrate-limiter](https://github.com/vutran1710/PyrateLimiter/tree/v3.9.0) with `use_file_lock=True`.

It can handdle many connections concurrently and respect the chosen limits `per_second`, `per_minute`, `per_day`.

## class Communicate

### **init**

- `session: requests.Session` (**Required**)
- `caller_name: str  (limiter id)` (**Required**)
- `per_second: int = 1`
- `per_minute: int = 56`
- `per_day: Optional[int] = None`
- `stream: bool = False`
- `timeout: Union[float, tuple] = 5`
- `allow_redirects: bool = True`

### send

- `method: str` (**Required**)
- `url: str` (**Required**)
- `headers: Optional[dict] = None` (default headers are sent if None)
- `**kwargs` (accepted by `requests.Request`)

## Examples

- Simplest (by default: 56 requests per minute, 1 request per second):

  ```
  from api import Communicate
  from requests import Session

  session = Session()

  response = Communicate(session=session, caller_name="simple_john").send(
      method="GET", url="https://john-site.com"
  )
  ```

- With custom limits and custom headers:

  ```
  from api import Communicate
  from requests import Session

  session = Session()
  headers = {"User-Agent": ("My Dear Agent v.1")}

  response = Communicate(session=session, caller_name="John", per_minute=6).send(
      method="GET", url="https://mysite.com", headers=headers
  )
  ```
