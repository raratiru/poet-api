# poet-api

Requests with Limiter.

Uses `pyrate_limiter.SQLiteBucket` with `use_file_lock=True`.

It can handle many connections concurrently and respect the chosen limits `per_second`, `per_minute`, `per_day`.

## class Communicate

### **init**

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
- `session: requests.Session = None`
- `headers: Optional[dict] = None` (default headers are sent if None)
- `**kwargs` (accepted by `requests.Request`)

## Examples

- Simplest (by default: 56 requests per minute, 1 request per second):

  ```python
  import requests

  from api import Communicate
  from requests import Session

  limiter = Communicate(caller_name="simple_john")

  response: requests.Response = limiter.send(
      method="GET", url="https://john-site.com"
  )
  ```

- With custom limits, session and custom headers:

  ```python
  from api import Communicate
  from requests import Session

  limiter = Communicate(
          caller_name="John",
          per_second=1,
          per_minute=6
      )
  headers = {"User-Agent": ("My Dear Agent v.1")}

  with Session() as session:
      response: requests.Response = limiter.send(
          method="GET",
          url="https://mysite.com",
          session=session,
          headers=headers
      )
  ```
