#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from time import sleep
from typing import Optional, Union

import requests  # type: ignore
from pyrate_limiter import Duration, Limiter, Rate, SQLiteBucket

logger = logging.getLogger(__name__)

import logging
from time import sleep
from typing import Optional, Union

import requests  # type: ignore
from pyrate_limiter import Duration, Limiter, Rate, SQLiteBucket

logger = logging.getLogger(__name__)

per_second_rate = Rate(1, Duration.SECOND)
per_minute_rate = Rate(56, Duration.MINUTE)

rates = [per_second_rate, per_minute_rate]

bucket = SQLiteBucket.init_from_file(
    rates, use_file_lock=True, db_path="pyrate_limiter.sqlite"
)

global_limiter = Limiter(bucket, raise_when_fail=False, max_delay=4000)
global_limiter.retry_until_max_delay = True

# counter = 1
# for _ in range(70):
#     global_limiter.try_acquire("item")
#     print(counter)
#     counter += 1


def communicate(
    session: requests.Session,
    request: requests.PreparedRequest,
    caller_name: str,
    limiter: Limiter,
    **kwargs,
) -> requests.Response:

    request_sent = False
    retry_counter = 0

    while not request_sent:
        try:
            limiter.try_acquire(caller_name)
            response = session.send(
                request,
                **kwargs,
            )
            request_sent = True
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            """Catches all exceptions that are safe to retry"""
            retry_counter = retry_counter + 1
            logger.info(
                f"ConnectionTimeout: Waiting {2 * (2 ** (retry_counter - 1))} "
                "seconds to retry"
            )
            sleep(2 * (2 ** (retry_counter - 1)))
            if retry_counter > 10:
                raise requests.exceptions.ConnectTimeout("Tried 10 times and failed")

    return response


class Communicate:
    """
    * Prepares a requests.Request.
    * Gets initialized with a requests.Session
    * Applies headers
    * Optionally accepts a limiter, otherwise the default limiter applies
    """

    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0"
        )
    }

    def __init__(
        self,
        session: requests.Session,
        caller_name: str,
        limiter: Optional[Limiter] = None,
        stream: bool = False,
        timeout: Union[float, tuple] = 5,
        allow_redirects: bool = True,
    ) -> None:
        self.session = self._validate_session(session)
        self.stream = stream
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.caller_name = caller_name
        self.limiter = limiter

    def _validate_session(self, session) -> requests.Session:
        if not issubclass(session.__class__, requests.Session):
            raise TypeError("A requests.Session is expected")
        return session

    def send(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Prepares a requests.Request object
        """
        request = self.session.prepare_request(
            requests.Request(
                method=method,
                url=url,
                headers=headers or self.default_headers,
                **kwargs,
            )
        )
        return communicate(
            self.session,
            request,
            caller_name=self.caller_name,
            limiter=self.limiter or global_limiter,
            stream=self.stream,
            timeout=self.timeout,
            allow_redirects=self.allow_redirects,
        )
