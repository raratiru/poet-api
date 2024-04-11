#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from time import sleep
from typing import Optional, Union
from urllib.parse import urlparse

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

    request_sent = False
    retry_counter = 0

    while not request_sent:
        try:
            with limiter.ratelimit(caller_name, delay=True):
                p_url = urlparse(request.url)
                limiters = ", ".join([rate.__str__() for rate in limiter._rates])
                logger.debug("\n\n***Request Information***")
                logger.debug(f"* Sending request now {datetime.now().isoformat()}")
                logger.debug(
                    f"Url: {p_url.scheme}://{p_url.netloc}{p_url.path} (/?...)"
                )
                logger.debug(f"Limiters: {limiters}")
                logger.debug("\n***/Request Information***\n\n")
                response = session.send(
                    request,
                    **kwargs,
                )
                request_sent = True
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            """ Catches all exceptions that are safe to retry """
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
