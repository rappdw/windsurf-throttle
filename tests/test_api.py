"""Tests for the Windsurf API client."""

import pytest

from windsurf_throttle.api import WindsurfAPIError


def test_api_error_message() -> None:
    """Test that WindsurfAPIError stores the message correctly."""
    error = WindsurfAPIError("test error message")
    assert str(error) == "test error message"


def test_get_usage_config_requires_target() -> None:
    """Test that get_usage_config raises without a target."""
    from windsurf_throttle.api import get_usage_config

    with pytest.raises(WindsurfAPIError, match="Must specify one of"):
        get_usage_config()


def test_set_usage_config_requires_action() -> None:
    """Test that set_usage_config raises without an action."""
    from windsurf_throttle.api import set_usage_config

    with pytest.raises(WindsurfAPIError, match="Must specify either"):
        set_usage_config(team_level=True)
