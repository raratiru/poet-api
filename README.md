# poet-api

Requests with Limiter.

Uses `pyrate_limiter.SQLiteBucket` with `use_file_lock=True`.

It has a default `RATE_LIMIT_SITES` setting and waits for `settings.DJANGO_RATE_LIMIT_SITES`:

```python
RATE_LIMIT_SITES = {
    # "payment_gateway": {
    #     "domain_keyword": "adomain.com",
    #     "rates": [Rate(25, Duration.MINUTE)],
    #     "max_wait_seconds": 5,  # Custom timeout in seconds overrides Rate if abort_trying = False, else returns 429
    # },
    # "analytics_service": {
    #     "domain_keyword": "anotherdomain.com",
    #     "rates": [Rate(50, Duration.MINUTE)],
    #     # No timeout here: default = -1
    # },
    "default": {"rates": [Rate(59, Duration.MINUTE)], "max_wait_seconds": -1, "abort_trying": False},
}
```

## Configuration:
* `domain_keyword: str` -> Creates a limiter for this domain
* `rates: list` -> `Rate` objects for the domain
* `max_wait_seconds: int` -> Max seconds the limiter can wait for the domain
* `abort_trying: bool` -> 
     `False` -> If "rates" demands more time than "max_wait_seconds", the request is fired asap
     `True` -> If "rates" demands more time than "max_wait_seconds", a mocked 429 Response is returned with a custom object.

## Example

  ```python
  from api.rate_limiter import send_request
  import requests
  
  try:
      # 1. Send request
      response = send_request("https://example.com", method="POST", json={"amount": 10})
      
      # 2. Raise for error
      # If:
      #   - max_wait_seconds != -1 (-1 is the default) 
      #   - abort_trying is True 
      #   - the bucket cannot afford it
      # -> a mocked 429 response is returned
      # If the request errored -> HTTPError.
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
