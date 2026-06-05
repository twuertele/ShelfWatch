"""Sensor platform for ShelfWatch."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ACCOUNT_NAME,
    CONF_BASE_URL,
    CONF_ENABLE_TODO_LIST,
    DEFAULT_ENABLE_TODO_LIST,
    DOMAIN,
)
from .coordinator import ShelfWatchCoordinator
from .koha_client import KohaAccountData


@dataclass(frozen=True, kw_only=True)
class ShelfWatchSensorEntityDescription(SensorEntityDescription):
    """ShelfWatch sensor description."""

    value_fn: Callable[[KohaAccountData], Any]
    extra_attrs_fn: Callable[[KohaAccountData], dict[str, Any]] | None = None


def _account_attrs(data: KohaAccountData) -> dict[str, Any]:
    """Return rich account attributes for the checkout count sensor."""
    return {
        "status": data.status,
        "next_due_date": data.next_due_date,
        "next_due_iso": data.next_due_iso,
        "next_due_in_days": data.next_due_in_days,
        "overdue_count": data.overdue_count,
        "due_soon_count": data.due_soon_count,
        "due_today_count": data.due_today_count,
        "last_update": data.last_update,
        "books": [book.as_dict() for book in data.books],
        "overdue_books": [book.as_dict() for book in data.overdue_books],
        "due_today_books": [book.as_dict() for book in data.due_today_books],
        "due_soon_books": [book.as_dict() for book in data.due_soon_books],
    }


def _last_update_attr(data: KohaAccountData) -> dict[str, Any]:
    return {"last_update": data.last_update}


def _books_attr(data: KohaAccountData) -> dict[str, Any]:
    return {
        "last_update": data.last_update,
        "books": [book.as_dict() for book in data.books],
    }


def _status_attr(data: KohaAccountData) -> dict[str, Any]:
    return {
        "checkout_count": data.checkout_count,
        "next_due_date": data.next_due_date,
        "next_due_in_days": data.next_due_in_days,
        "overdue_count": data.overdue_count,
        "due_today_count": data.due_today_count,
        "due_soon_count": data.due_soon_count,
        "overdue_books": [book.as_dict() for book in data.overdue_books],
        "due_today_books": [book.as_dict() for book in data.due_today_books],
        "due_soon_books": [book.as_dict() for book in data.due_soon_books],
        "last_update": data.last_update,
    }


def _last_update_value(data: KohaAccountData) -> datetime | None:
    if not data.last_update:
        return None
    return datetime.fromisoformat(data.last_update.replace("Z", "+00:00"))


SENSORS: tuple[ShelfWatchSensorEntityDescription, ...] = (
    ShelfWatchSensorEntityDescription(
        key="checkout_count",
        translation_key="checkout_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.checkout_count,
        extra_attrs_fn=_account_attrs,
    ),
    ShelfWatchSensorEntityDescription(
        key="next_due_date",
        translation_key="next_due_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: (
            date.fromisoformat(data.next_due_date) if data.next_due_date else None
        ),
        extra_attrs_fn=lambda data: {
            "next_due_iso": data.next_due_iso,
            "next_due_in_days": data.next_due_in_days,
            "last_update": data.last_update,
        },
    ),
    ShelfWatchSensorEntityDescription(
        key="next_due_in_days",
        translation_key="next_due_in_days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.next_due_in_days,
        extra_attrs_fn=lambda data: {
            "next_due_date": data.next_due_date,
            "next_due_iso": data.next_due_iso,
            "last_update": data.last_update,
        },
    ),
    ShelfWatchSensorEntityDescription(
        key="overdue_count",
        translation_key="overdue_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.overdue_count,
        extra_attrs_fn=lambda data: {
            "last_update": data.last_update,
            "books": [book.as_dict() for book in data.overdue_books],
        },
    ),
    ShelfWatchSensorEntityDescription(
        key="due_today_count",
        translation_key="due_today_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.due_today_count,
        extra_attrs_fn=lambda data: {
            "last_update": data.last_update,
            "books": [book.as_dict() for book in data.due_today_books],
        },
    ),
    ShelfWatchSensorEntityDescription(
        key="due_soon_count",
        translation_key="due_soon_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.due_soon_count,
        extra_attrs_fn=lambda data: {
            "last_update": data.last_update,
            "books": [book.as_dict() for book in data.due_soon_books],
        },
    ),
    ShelfWatchSensorEntityDescription(
        key="status",
        translation_key="status",
        value_fn=lambda data: data.status,
        extra_attrs_fn=_status_attr,
    ),
    ShelfWatchSensorEntityDescription(
        key="books",
        translation_key="books",
        native_unit_of_measurement="items",
        value_fn=lambda data: data.checkout_count,
        extra_attrs_fn=_books_attr,
    ),
    ShelfWatchSensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_update_value,
        extra_attrs_fn=_last_update_attr,
    ),
    ShelfWatchSensorEntityDescription(
        key="completed_count",
        translation_key="completed_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.completed_count,
    ),
    ShelfWatchSensorEntityDescription(
        key="remaining_count",
        translation_key="remaining_count",
        native_unit_of_measurement="items",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.remaining_count,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShelfWatch sensors."""
    coordinator: ShelfWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    todo_enabled = entry.options.get(
        CONF_ENABLE_TODO_LIST, DEFAULT_ENABLE_TODO_LIST
    )
    async_add_entities(
        ShelfWatchSensor(coordinator, entry, description)
        for description in SENSORS
        if todo_enabled or description.key not in {"completed_count", "remaining_count"}
    )


class ShelfWatchSensor(CoordinatorEntity[ShelfWatchCoordinator], SensorEntity):
    """ShelfWatch sensor backed by the account coordinator."""

    entity_description: ShelfWatchSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ShelfWatchCoordinator,
        entry: ConfigEntry,
        description: ShelfWatchSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        account_name = entry.data[CONF_ACCOUNT_NAME]
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": account_name,
            "model": "Online-Bibliothekskonto",
            "configuration_url": entry.data[CONF_BASE_URL],
        }
        if description.key in {
            "books",
            "due_today_count",
            "last_update",
            "overdue_count",
            "status",
            "due_soon_count",
            "completed_count",
            "remaining_count",
        }:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional sensor attributes."""
        if self.entity_description.extra_attrs_fn is None:
            return None
        return self.entity_description.extra_attrs_fn(self.coordinator.data)
