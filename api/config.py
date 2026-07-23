from pyrate_limiter import Duration, Rate

# Guaranteed core default backup configuration
CORE_DEFAULT_CONFIG = {
    "rates": [Rate(59, Duration.MINUTE)],
    "max_wait_seconds": -1,
    "abort_trying": False,
}

# The global settings dictionary utilized by the infrastructure
RATE_LIMIT_SITES = {"default": CORE_DEFAULT_CONFIG.copy()}


def load_django_settings(target_dict: dict) -> None:
    """
    Safely discovers and extracts DJANGO_RATE_LIMIT_SITES settings,
    updating the target dictionary while keeping strict type validation.
    """
    try:
        from django.conf import settings

        # Accessing configured variable checks if django context is initialized
        if settings.configured:
            user_sites = getattr(settings, "DJANGO_RATE_LIMIT_SITES", {})
            if isinstance(user_sites, dict):
                target_dict.update(user_sites)
    except Exception:
        # Safely trap ImproperlyConfigured exception in pure test runs
        pass

    # Defensive validation: Enforce core defaults layout if corrupted or missing
    if (
        "default" not in target_dict
        or not isinstance(target_dict["default"], dict)
        or "rates" not in target_dict["default"]
    ):
        target_dict["default"] = CORE_DEFAULT_CONFIG.copy()


# Trigger initial dynamic setup on module load
load_django_settings(RATE_LIMIT_SITES)
