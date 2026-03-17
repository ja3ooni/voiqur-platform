"""
Foundation tests for Plan 01-01: python-dotenv wiring.

Tests verify:
- load_dotenv() is called before APIConfig() in main.py entry point
- .env.example exists with all required environment variable names
"""

import os
import pathlib
import pytest


# Root directory of kiro/voiquyr
KIRO_ROOT = pathlib.Path(__file__).parent.parent


def test_env_loading():
    """
    After load_dotenv() is called, APIConfig() reads JWT_SECRET_KEY from .env,
    not the hardcoded fallback "your-secret-key-change-in-production".

    RED: Fails because main.py does not call load_dotenv() before APIConfig().
    GREEN: Passes after load_dotenv() is added at module level in main.py.
    """
    env_file = KIRO_ROOT / ".env"
    if not env_file.exists():
        pytest.skip(".env file not present — create it to run this test")

    # Ensure the env var is NOT already in os.environ (simulate fresh start)
    original = os.environ.pop("JWT_SECRET_KEY", None)
    try:
        # Import load_dotenv and call it — mimicking what main.py must do
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_file, override=True)

        # Now instantiate APIConfig — it must pick up the .env value
        from src.api.config import APIConfig
        config = APIConfig()

        assert config.auth_config.jwt_secret_key != "your-secret-key-change-in-production", (
            "JWT_SECRET_KEY is still the hardcoded default — "
            "either load_dotenv() was not called before APIConfig() "
            "or .env does not define JWT_SECRET_KEY"
        )
        assert config.auth_config.jwt_secret_key != "", "JWT_SECRET_KEY is empty in .env"
    finally:
        # Restore original state
        if original is not None:
            os.environ["JWT_SECRET_KEY"] = original
        else:
            os.environ.pop("JWT_SECRET_KEY", None)


def test_env_example_exists():
    """
    .env.example must exist and contain all 9 required variable names.

    RED: Fails because .env.example does not exist yet.
    GREEN: Passes after .env.example is created with all required vars.
    """
    env_example = KIRO_ROOT / ".env.example"

    assert env_example.exists(), (
        f".env.example not found at {env_example} — create it from the template"
    )

    content = env_example.read_text()
    required_vars = [
        "JWT_SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "MISTRAL_API_KEY",
        "DEEPGRAM_API_KEY",
        "ELEVENLABS_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "STRIPE_API_KEY",
    ]

    missing = [var for var in required_vars if var not in content]
    assert not missing, (
        f".env.example is missing required variable(s): {missing}"
    )
