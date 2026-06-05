"""ShelfWatch Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_TODO_LIST,
    DEFAULT_ENABLE_TODO_LIST,
    DOMAIN,
)
from .coordinator import ShelfWatchCoordinator
from .settings import enabled_platforms


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ShelfWatch from a config entry."""
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    coordinator = ShelfWatchCoordinator(hass, entry)
    await coordinator.async_load_progress()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    coordinator.platforms = _platforms(entry)
    await hass.config_entries.async_forward_entry_setups(entry, coordinator.platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a ShelfWatch config entry."""
    coordinator: ShelfWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, coordinator.platforms
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload ShelfWatch when config entry options change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _platforms(entry: ConfigEntry) -> list[str]:
    """Return enabled platforms for a config entry."""
    return enabled_platforms(
        entry.options.get(CONF_ENABLE_TODO_LIST, DEFAULT_ENABLE_TODO_LIST)
    )
