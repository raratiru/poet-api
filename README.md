# poet-api

Requests with Limiter.

Uses `pyrate_limiter.SQLiteBucket` with `use_file_lock=True`.

It has a default `RATE_LIMIT_SITES` setting and waits for `settings.DJANGO_RATE_LIMIT_SITES`:

## Configuration:
```python
DJANGO_RATE_LIMIT_SITES = {
    "payment_gateway": {
        "domain_keyword": "adomain.com",
        "rates": [Rate(25, Duration.MINUTE)],
        "max_wait_seconds": 5,  # Custom timeout in seconds
    },
    "analytics_service": {
        "domain_keyword": "anotherdomain.com",
        "rates": [Rate(50, Duration.MINUTE)],
        # No timeout here: default = -1
    },
    # The following line, already exists as default setting:
    # "default": {"rates": [Rate(59, Duration.MINUTE)], "max_wait_seconds": -1},
}
```

* `DJANGO_RATE_LIMIT_SITES.keys()[0]: str` -> Unique identity keyword
* `DJANGO_RATE_LIMIT_SITES.values()[0]: dict` ->
    * `domain_keyword: str` -> `urlparse(url).netlock or "default"`. A new autonomous limiter is based on this keyword.
    * `rates: list` -> List of `Rate` objects for the `domain_keyword`
    * `max_wait_seconds: int` -> Max seconds the limiter can wait before failing.
        *  *-1*: Wait until the bucket allows a request, the request **never fails**.
        *  *positive int*: If the bucket needs more than `positive int` seconds to allow a request, the request **fails**.
            * A mocked `HTTP 429 ("Too Many Requests")` response object is returned **without making** an actual request.
            * `requests().raise_for_status()` raises `requests.exceptions.HTTPError`.

## Example

  ```python
  import requests

  from api.rate_limiter import send_request
  
  try:
      # 1. Send request
      response = send_request("https://example.com", method="POST", json={"amount": 10})
      
      # 2. Raise for error
      # If:
      #   - max_wait_seconds != -1 (-1 is the default) 
      #   - the bucket cannot afford it
      # -> a mocked HTTP 429 ("Too Many Requests") response is returned

      response.raise_for_status()
      
      # 3. Continue if everything is OK
      data = response.json()
      print("Success:", data)
  
  except requests.exceptions.HTTPError as e:
      print(f"HTTP Error occurred: {e}")
      if e.response and e.response.status_code == 429:
          print("Reason: The application queue was too full and exceeded max_wait_seconds!")
          
  except Exception as e:
      print(f"An unexpected error occurred: {e}")
    ```
