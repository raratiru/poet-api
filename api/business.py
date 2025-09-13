#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from pathlib import Path
from tempfile import gettempdir
from time import sleep
from typing import Optional, Union

import requests  # type: ignore
from pyrate_limiter import (
    AbstractBucket,
    BucketAsyncWrapper,
    Duration,
    Limiter,
    Rate,
    SQLiteBucket,
)

logger = logging.getLogger(__name__)


def create_sqlite_limiter(
    per_second: int = 1,
    per_minute: int = 56,
    per_day: Optional[int] = None,
    table_name: str = "rate_bucket",
    max_delay: Union[int, Duration] = Duration.DAY,
    buffer_ms: int = 50,
    use_file_lock: bool = True,
    async_wrapper: bool = False,
) -> Limiter:
    """
    Create a SQLite-backed rate limiter with configurable rate, persistence, and optional async support.

    Args:
        rate_per_duration: Number of allowed requests per duration.
        duration: Time window for the rate limit.
        db_path: Path to the SQLite database file (or in-memory if None).
        table_name: Name of the table used for rate buckets.
        max_delay: Maximum delay before failing requests.
        buffer_ms: Extra wait time in milliseconds to account for clock drift.
        use_file_lock: Enable file locking for multi-process synchronization.
        async_wrapper: Whether to wrap the bucket for async usage.

    Returns:
        Limiter: Configured SQLite-backed limiter instance.
    """
    per_second_rate = Rate(per_second, Duration.SECOND)
    per_minute_rate = Rate(per_minute, Duration.MINUTE)
    rate_limits = [per_second_rate, per_minute_rate]
    if per_day:
        per_day_rate = Rate(per_day, Duration.DAY)
        rate_limits.append(per_day_rate)

    temp_dir = Path(gettempdir())
    db_path = str(temp_dir / "pyrate_limiter.sqlite")

    bucket: AbstractBucket = SQLiteBucket.init_from_file(
        rate_limits,
        db_path=str(db_path),
        table=table_name,
        create_new_table=True,
        use_file_lock=use_file_lock,
    )

    if async_wrapper:
        bucket = BucketAsyncWrapper(bucket)

    limiter = Limiter(
        bucket,
        raise_when_fail=False,
        max_delay=max_delay,
        retry_until_max_delay=True,
        buffer_ms=buffer_ms,
    )

    return limiter


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
            limiter=self.limiter or create_sqlite_limiter(),
            stream=self.stream,
            timeout=self.timeout,
            allow_redirects=self.allow_redirects,
        )
