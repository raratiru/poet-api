#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from typing import Optional, Union

import requests  # type: ignore
from pyrate_limiter import Duration, FileLockSQLiteBucket, Limiter, RequestRate

logger = logging.getLogger(__name__)

global_limiter = Limiter(
    RequestRate(1, Duration.SECOND),  # Helps keep flowing with minimal delays
    RequestRate(56, Duration.MINUTE),  # Main limiter with safety zone
    bucket_class=FileLockSQLiteBucket,
)


def communicate(
    session: requests.Session,
    request: requests.PreparedRequest,
    caller_name: str,
    limiter: Limiter,
    **kwargs,
) -> requests.Response:

    with limiter.ratelimit(caller_name, delay=True):
        logger.debug(f"\n\n***Sending request now {datetime.now().isoformat()}***\n\n")
        response = session.send(
            request,
            **kwargs,
        )

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
