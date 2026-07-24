import logging
import os
import tempfile
from urllib.parse import urlparse

import requests
from pyrate_limiter import (
    AbstractBucket,
    BucketFactory,
    Limiter,
    MonotonicClock,
    RateItem,
    SQLiteBucket,
)

from api.config import RATE_LIMIT_SITES

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(tempfile.gettempdir(), "poet_api_rate_limit_data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "global_limits.sqlite")

clock = MonotonicClock()


class IsolatedDomainBucketFactory(BucketFactory):
    def __init__(self):
        super().__init__()
        self.buckets = {}

    def get_identity(self, url: str) -> str:
        """Maps incoming URLs to abstract configuration keys based on domain keywords."""
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc or "default"

        for key, config in RATE_LIMIT_SITES.items():
            if isinstance(config, dict):
                keyword = config.get("domain_keyword")
                if isinstance(keyword, str) and keyword in netloc:
                    return key

        return "default"

    def wrap_item(self, name: str, weight: int = 1) -> RateItem:
        """Stamps the abstract configuration key into a valid v4 RateItem wrapper."""
        return RateItem(name, clock.now(), weight=weight)

    def get(self, item: RateItem) -> AbstractBucket:
        """Provisions an isolated SQLite table in the temp directory backend."""
        config_key = item.name

        if config_key not in self.buckets:
            site_config = RATE_LIMIT_SITES.get(config_key, RATE_LIMIT_SITES["default"])
            rates = site_config["rates"]

            table_name = f"rate_{config_key}"

            self.buckets[config_key] = SQLiteBucket.init_from_file(
                rates=rates,
                table=table_name,
                db_path=DB_PATH,
                create_new_table=True,
                use_file_lock=True,
            )

        return self.buckets[config_key]


# Singleton infrastructure setup
factory = IsolatedDomainBucketFactory()
global_limiter = Limiter(factory)


def send_request(url: str, method: str = "POST", **kwargs):
    """
    Sync Hook for v4. Dynamically throttles requests based on application max wait time.
    Returns a custom 429 Mock Response if the calculated queue wait time exceeds constraints.
    """
    config_key = factory.get_identity(url)
    site_config = RATE_LIMIT_SITES.get(config_key, RATE_LIMIT_SITES["default"])

    # Read the custom wait time configuration, falling back to infinate (-1)
    max_wait = site_config.get("max_wait_seconds", -1)

    # Executing try_acquire: blocks to wait if within limits, returns False if wait is too long
    is_acquired = global_limiter.try_acquire(config_key, timeout=max_wait)

    if not is_acquired:
        # Fail Fast: The queue wait time exceeds your program's willingness to wait
        logger.error(
            f"Queue wait time for {config_key} exceeds max_wait_seconds of {max_wait}s! Aborting."
        )

        class QueueTimeoutResponse:
            status_code = 429
            text = "Application queue wait timeout exceeded."

            def raise_for_status(self):
                raise requests.exceptions.HTTPError("429 Client Error: Queue Timeout")

        return QueueTimeoutResponse()

    # Proceed to execute request only if a token was safely locked down
    response = requests.request(method, url, **kwargs)
    return response
