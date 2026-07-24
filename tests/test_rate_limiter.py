import pytest
from pyrate_limiter import Duration, Rate, RateItem

from api import rate_limiter
from api.config import CORE_DEFAULT_CONFIG, load_django_settings

MOCK_FULL_CONFIG = {
    "test_gateway": {
        "domain_keyword": "teststripe.com",
        "rates": [Rate(10, Duration.MINUTE)],
        "max_wait_seconds": 2,
    },
    "test_analytics": {
        "domain_keyword": "testmixpanel.com",
        "rates": [Rate(5, Duration.MINUTE)],
    },
    "default": {"rates": [Rate(1, Duration.SECOND)]},
}

MOCK_BAD_TYPE_CONFIG = {
    "invalid_key_format": "this_should_be_a_dict_but_is_a_string",
    "default": {"rates": [Rate(1, Duration.SECOND)]},
}


@pytest.fixture(autouse=True)
def clean_factory_cache():
    """Clears factory cache before and after every test run to keep environment pristine."""
    rate_limiter.factory.buckets.clear()
    yield
    rate_limiter.factory.buckets.clear()


class TestConfigInitialization:
    def test_load_django_settings_success(self, monkeypatch):
        """
        UNLOCKS LINES 24-29: Simulates a fully active Django settings setup
        to ensure custom dictionary payloads are successfully merged.
        """

        class MockSettings:
            configured = True
            DJANGO_RATE_LIMIT_SITES = {
                "mock_site": {
                    "domain_keyword": "mock.com",
                    "rates": [Rate(1, Duration.SECOND)],
                }
            }

        # Patch the settings inside the module namespace safely
        monkeypatch.setattr("django.conf.settings", MockSettings, raising=False)

        sample_dict = {"default": CORE_DEFAULT_CONFIG.copy()}
        load_django_settings(sample_dict)

        assert "mock_site" in sample_dict
        assert sample_dict["default"] == CORE_DEFAULT_CONFIG

    def test_load_django_settings_defensive_fallback(self, monkeypatch):
        """
        UNLOCKS LINE 41: Simulates a corrupt initialization where 'default' is
        completely missing, forcing the function to rebuild it dynamically.
        """

        class MockSettings:
            configured = True
            DJANGO_RATE_LIMIT_SITES = {"bad_key": "not_a_dict"}

        monkeypatch.setattr("django.conf.settings", MockSettings, raising=False)

        # Intentionally passing a dictionary that breaks the configuration rules
        corrupted_dict = {"invalid_data": True}
        load_django_settings(corrupted_dict)

        # Line 41 fallback should trigger and safely reconstruct the default structure
        assert "default" in corrupted_dict
        assert corrupted_dict["default"] == CORE_DEFAULT_CONFIG


class TestIsolatedDomainBucketFactory:
    def test_get_identity_with_matching_keyword(self, monkeypatch):
        """Forces a scenario where a custom domain keyword is found and immediately matched."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)

        test_factory = rate_limiter.IsolatedDomainBucketFactory()
        assert test_factory.get_identity("https://teststripe.com") == "test_gateway"

    def test_get_identity_loop_exhaustion_returns_default(self, monkeypatch):
        """Forces the loop to evaluate all custom keys, find no matches, and fall back to default."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)

        test_factory = rate_limiter.IsolatedDomainBucketFactory()
        assert (
            test_factory.get_identity("https://completely-unrelated-domain.com")
            == "default"
        )

    def test_get_identity_invalid_config_type_branch(self, monkeypatch):
        """Forces the loop to hit an item that is NOT a dictionary, completing branch analysis."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_BAD_TYPE_CONFIG)

        test_factory = rate_limiter.IsolatedDomainBucketFactory()
        assert test_factory.get_identity("https://teststripe.com") == "default"

    def test_get_identity_invalid_string(self):
        """Verifies that strings missing standard URL nets safely route to the default block."""
        test_factory = rate_limiter.IsolatedDomainBucketFactory()
        assert test_factory.get_identity("invalid_string_format") == "default"

    def test_wrap_item(self):
        """Verifies correct RateItem data formatting."""
        test_factory = rate_limiter.IsolatedDomainBucketFactory()
        result = test_factory.wrap_item("abstract_key", 1)
        assert isinstance(result, RateItem)
        assert result.name == "abstract_key"

    def test_bucket_creation_and_memory_caching(self, monkeypatch):
        """Validates lazy initialization and consistent reference retrieval from memory caches."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)
        test_factory = rate_limiter.IsolatedDomainBucketFactory()

        mock_item = test_factory.wrap_item("test_gateway")
        bucket_one = test_factory.get(mock_item)
        assert "test_gateway" in test_factory.buckets

        bucket_two = test_factory.get(mock_item)
        assert bucket_one is bucket_two


class TestSafeApiSend:
    def test_send_request_uses_custom_configured_timeout(self, mocker, monkeypatch):
        """Asserts that custom setting timeouts are accurately extracted and assigned to try_acquire."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)
        mock_acquire = mocker.patch.object(
            rate_limiter.global_limiter, "try_acquire", return_value=True
        )
        mocker.patch("rate_limiter.requests.request")

        rate_limiter.send_request("https://teststripe.com", method="GET")

        mock_acquire.assert_called_once()
        args, kwargs = mock_acquire.call_args
        assert args == ("test_gateway",)
        assert kwargs.get("timeout") == 2

    def test_send_request_applies_fallback_timeout(self, mocker, monkeypatch):
        """Asserts that absence of site-specific timeouts seamlessly enforces the -1 second default."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)
        mock_acquire = mocker.patch.object(
            rate_limiter.global_limiter, "try_acquire", return_value=True
        )
        mocker.patch("rate_limiter.requests.request")

        rate_limiter.send_request("https://testmixpanel.com", method="POST")

        mock_acquire.assert_called_once()
        args, kwargs = mock_acquire.call_args
        assert args == ("test_analytics",)
        assert kwargs.get("timeout") == -1

    def test_send_request_returns_429_on_queue_timeout(self, mocker, monkeypatch):
        """Verifies that when try_acquire returns False, a mock 429 response object is built."""
        monkeypatch.setattr(rate_limiter, "RATE_LIMIT_SITES", MOCK_FULL_CONFIG)
        mocker.patch.object(
            rate_limiter.global_limiter, "try_acquire", return_value=False
        )
        mock_requests = mocker.patch("rate_limiter.requests.request")

        response = rate_limiter.send_request("https://teststripe.com", method="GET")

        mock_requests.assert_not_called()
        assert response.status_code == 429
        assert "timeout exceeded" in response.text
