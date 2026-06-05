"""Constants for the ShelfWatch integration."""

from __future__ import annotations

DOMAIN = "shelfwatch"

DEFAULT_BASE_URL = "https://sb-muehlacker.lmscloud.net"
DEFAULT_UPDATE_INTERVAL_HOURS = 24
DEFAULT_DUE_SOON_DAYS = 7
DEFAULT_ENABLE_TODO_LIST = False
DEFAULT_COMPLETE_RETURNED_ITEMS = False
DEFAULT_KEEP_COMPLETED_ITEMS = False

CONF_ACCOUNT_NAME = "account_name"
CONF_BASE_URL = "base_url"
CONF_USER_ID = "user_id"
CONF_PASSWORD = "password"
CONF_DUE_SOON_DAYS = "due_soon_days"
CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"
CONF_ENABLE_TODO_LIST = "enable_todo_list"
CONF_COMPLETE_RETURNED_ITEMS = "complete_returned_items"
CONF_KEEP_COMPLETED_ITEMS = "keep_completed_items"

PLATFORM_SENSOR = "sensor"
PLATFORM_TODO = "todo"
