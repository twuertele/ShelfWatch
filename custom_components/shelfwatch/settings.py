"""Option handling helpers for ShelfWatch."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_COMPLETE_RETURNED_ITEMS,
    CONF_DUE_SOON_DAYS,
    CONF_ENABLE_TODO_LIST,
    CONF_KEEP_COMPLETED_ITEMS,
    CONF_UPDATE_INTERVAL_HOURS,
    PLATFORM_SENSOR,
    PLATFORM_TODO,
)

CONF_DUE_DATES_AND_UPDATES = "due_dates_and_updates"
CONF_READING_PROGRESS = "reading_progress"


def normalize_options_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten option sections and enforce dependent Todo settings."""
    options = {
        **user_input[CONF_DUE_DATES_AND_UPDATES],
        **user_input[CONF_READING_PROGRESS],
    }
    options[CONF_DUE_SOON_DAYS] = int(options[CONF_DUE_SOON_DAYS])
    options[CONF_UPDATE_INTERVAL_HOURS] = int(options[CONF_UPDATE_INTERVAL_HOURS])
    options[CONF_ENABLE_TODO_LIST] = bool(options[CONF_ENABLE_TODO_LIST])
    options[CONF_COMPLETE_RETURNED_ITEMS] = bool(
        options[CONF_COMPLETE_RETURNED_ITEMS]
    )
    options[CONF_KEEP_COMPLETED_ITEMS] = bool(options[CONF_KEEP_COMPLETED_ITEMS])

    if not options[CONF_ENABLE_TODO_LIST]:
        options[CONF_COMPLETE_RETURNED_ITEMS] = False
        options[CONF_KEEP_COMPLETED_ITEMS] = False
    elif not options[CONF_COMPLETE_RETURNED_ITEMS]:
        options[CONF_KEEP_COMPLETED_ITEMS] = False

    return options


def enabled_platforms(todo_enabled: bool) -> list[str]:
    """Return the platforms enabled for one ShelfWatch account."""
    platforms = [PLATFORM_SENSOR]
    if todo_enabled:
        platforms.append(PLATFORM_TODO)
    return platforms
