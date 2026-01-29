"""Windsurf API client for credit cap management."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("WINDSURF_BASE_URL", "https://server.codeium.com")
SERVICE_KEY = os.getenv("WINDSURF_SERVICE_KEY")

BASE_CREDITS = 500
DEFAULT_ORG_ADDON_CAP = 1000
DEFAULT_INDIVIDUAL_CAP_THRESHOLD = 1000
DEFAULT_INDIVIDUAL_CAP_BUFFER = 500


class WindsurfAPIError(Exception):
    """Exception raised for Windsurf API errors."""

    pass


def get_service_key() -> str:
    """Get the service key from environment, raising if not found."""
    if not SERVICE_KEY:
        raise WindsurfAPIError("WINDSURF_SERVICE_KEY not found in environment")
    return SERVICE_KEY


def get_usage_config(
    team_level: bool = False,
    group_id: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Get usage configuration via Windsurf API.

    Args:
        team_level: If True, get team-level configuration.
        group_id: Get configuration for a specific group.
        user_email: Get configuration for a specific user.

    Returns:
        API response as a dictionary.

    Raises:
        WindsurfAPIError: If the API call fails or no target is specified.
    """
    service_key = get_service_key()
    payload: dict[str, Any] = {"service_key": service_key}

    if team_level:
        payload["team_level"] = True
    elif group_id:
        payload["group_id"] = group_id
    elif user_email:
        payload["user_email"] = user_email
    else:
        raise WindsurfAPIError("Must specify one of: team_level, group_id, or user_email")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE_URL}/api/v1/GetUsageConfig",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise WindsurfAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise WindsurfAPIError(f"Error getting usage config: {e}")


def get_team_users(
    group_name: str | None = None,
    start_timestamp: str | None = None,
    end_timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Get list of team users via Windsurf API.

    Args:
        group_name: Filter results to users in a specific group (optional).
        start_timestamp: Start time in RFC 3339 format (optional).
        end_timestamp: End time in RFC 3339 format (optional).

    Returns:
        List of user statistics objects with name, email, etc.

    Raises:
        WindsurfAPIError: If the API call fails.
    """
    service_key = get_service_key()
    payload: dict[str, Any] = {"service_key": service_key}

    if group_name:
        payload["group_name"] = group_name
    if start_timestamp:
        payload["start_timestamp"] = start_timestamp
    if end_timestamp:
        payload["end_timestamp"] = end_timestamp

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{API_BASE_URL}/api/v1/UserPageAnalytics",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("userTableStats", [])
    except httpx.HTTPStatusError as e:
        raise WindsurfAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}") from e
    except Exception as e:
        raise WindsurfAPIError(f"Error getting team users: {e}") from e


def set_usage_config(
    set_add_on_credit_cap: int | None = None,
    clear_add_on_credit_cap: bool = False,
    team_level: bool = False,
    group_id: str | None = None,
    user_email: str | None = None,
) -> dict[str, Any]:
    """Set or clear add-on credit cap via Windsurf API.

    Args:
        set_add_on_credit_cap: The add-on credit cap to set.
        clear_add_on_credit_cap: If True, clear the add-on credit cap.
        team_level: If True, set team-level configuration.
        group_id: Set configuration for a specific group.
        user_email: Set configuration for a specific user.

    Returns:
        API response as a dictionary.

    Raises:
        WindsurfAPIError: If the API call fails or required args are missing.
    """
    service_key = get_service_key()
    payload: dict[str, Any] = {"service_key": service_key}

    if clear_add_on_credit_cap:
        payload["clear_add_on_credit_cap"] = True
    elif set_add_on_credit_cap is not None:
        payload["set_add_on_credit_cap"] = set_add_on_credit_cap
    else:
        raise WindsurfAPIError("Must specify either set_add_on_credit_cap or clear_add_on_credit_cap")

    if team_level:
        payload["team_level"] = True
    elif group_id:
        payload["group_id"] = group_id
    elif user_email:
        payload["user_email"] = user_email
    else:
        raise WindsurfAPIError("Must specify one of: team_level, group_id, or user_email")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE_URL}/api/v1/UsageConfig",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise WindsurfAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise WindsurfAPIError(f"Error setting usage config: {e}")
