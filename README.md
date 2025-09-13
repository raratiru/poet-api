# poet-api
Requests with Limiter

## class Communicate
  ### __init__

  * `session: requests.Session` (**Required**)
  * `caller_name: str  (limiter id)` (**Required**)
  * `limiter: Optional[Limiter] = None` (Default limiter uses `SQLiteBucket` 56 requests/minute)
  * `stream: bool = False`
  * `timeout: Union[float, tuple] = 5`
  * `allow_redirects: bool = True`

  ### send
  * `method: str` (**Required**)
  * `url: str` (**Required**)
  * `headers: Optional[dict] = None` (default headers are sent if None)
  * `**kwargs` (accepted by `requests.Request`)

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

- With limiter:

  ```
  from api import Communicate, create_sqlite_limiter
  from requests import Session

  session = Session()
  limiter = create_sqlite_limiter(per_second=1, per_minute=3, per_day=10)
  headers = {"User-Agent": ("My Dear Agent v.1")}

  response = Communicate(session=session, caller_name="John", limiter=limiter).send(
      method="GET", url="https://mysite.com", headers=headers
  )
  ```
