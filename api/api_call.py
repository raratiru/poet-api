import logging
from time import sleep

import requests

from api.protocols import ApiResponse
from api.rate_limiter import send_request

logger = logging.getLogger(__name__)

RETRIABLE_ERRORS = (
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.HTTPError,
)


def call_them(url: str, action: str, **kwargs) -> ApiResponse:
    retry_counter = 0

    while True:
        try:
            response = send_request(url=url, method=action.upper(), **kwargs)
            response.raise_for_status()
            return response

        except RETRIABLE_ERRORS as connection_error:
            retry_counter += 1

            if retry_counter > 10:
                logger.exception(
                    "Max retries exceeded for %s %s.",
                    action.upper(),
                    url,
                    extra={"tags": {"api_url": url, "api_action": action.upper()}},
                )
                raise

            wait_time = 2 * (2 ** (retry_counter - 1))
            error_name = type(connection_error).__name__
            logger.info(f"{error_name}: Waiting {wait_time} seconds to retry \n\n {connection_error}")

            sleep(wait_time)
