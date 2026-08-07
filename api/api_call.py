import logging
from collections.abc import Mapping
from time import sleep

import requests

from api.protocols import SyncHttpResponse
from api.rate_limiter import send_request

logger = logging.getLogger(__name__)

RETRIABLE_ERRORS = (
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
    # requests.exceptions.HTTPError,
)


class Response:
    def json(self):
        return "No response available because no response received"

    @property
    def status_code(self) -> int:
        return 400

    @property
    def headers(self) -> Mapping[str, str]:
        return {}

    @property
    def text(self) -> str:
        return "No response available because no response received"

    def raise_for_status(self):
        raise requests.exceptions.HTTPError(
            "400 Client Error: No response available because no response received"
        )


def call_them(url: str, action: str, **kwargs) -> SyncHttpResponse:
    retry_counter = 0
    response = Response()

    while True:
        try:
            response = send_request(url=url, method=action.upper(), **kwargs)
            response.raise_for_status()
            return response

        except RETRIABLE_ERRORS as connection_error:
            try:
                the_text = response.json()
            except requests.exceptions.JSONDecodeError:
                the_text = response.text

            retry_counter += 1
            if retry_counter > 10:
                logger.warning(
                    "Max retries exceeded for %s %s with message \n\n %s",
                    action.upper(),
                    url,
                    the_text,
                    extra={"tags": {"api_url": url, "api_action": action.upper()}},
                )
                return response

            wait_time = 2 * (2 ** (retry_counter - 1))
            error_name = type(connection_error).__name__
            logger.warning(
                f"{error_name}: Waiting {wait_time} seconds to retry \n\n {connection_error} \n\n {response.json()}"
            )

            sleep(wait_time)
        except requests.HTTPError:
            try:
                the_text = response.json()
            except requests.exceptions.JSONDecodeError:
                the_text = response.text

            logger.warning(
                "HTTPError occured for %s %s with message \n\n %s",
                action.upper(),
                url,
                the_text,
                extra={"tags": {"api_url": url, "api_action": action.upper()}},
            )
            return response
