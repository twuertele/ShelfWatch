"""DataUpdateCoordinator for ShelfWatch."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BASE_URL,
    CONF_COMPLETE_RETURNED_ITEMS,
    CONF_DUE_SOON_DAYS,
    CONF_KEEP_COMPLETED_ITEMS,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL_HOURS,
    CONF_USER_ID,
    DEFAULT_DUE_SOON_DAYS,
    DEFAULT_COMPLETE_RETURNED_ITEMS,
    DEFAULT_KEEP_COMPLETED_ITEMS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)
from .koha_client import (
    CannotConnect,
    InvalidAuth,
    KohaAccountData,
    KohaCheckout,
    KohaClient,
    build_account_data,
)
from .progress import progress_counts, synchronize_progress

_LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


class ShelfWatchCoordinator(DataUpdateCoordinator[KohaAccountData]):
    """Coordinator that fetches one library account."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.platforms: list[str] = []
        self._progress_store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.progress.{entry.entry_id}"
        )
        self._completed_items: dict[str, str] = {}
        self._archived_items: dict[str, dict[str, Any]] = {}
        self._known_items: dict[str, dict[str, Any]] = {}
        self._complete_returned_items = entry.options.get(
            CONF_COMPLETE_RETURNED_ITEMS, DEFAULT_COMPLETE_RETURNED_ITEMS
        )
        self._keep_completed_items = entry.options.get(
            CONF_KEEP_COMPLETED_ITEMS, DEFAULT_KEEP_COMPLETED_ITEMS
        )
        self._due_soon_days = entry.options.get(
            CONF_DUE_SOON_DAYS, DEFAULT_DUE_SOON_DAYS
        )
        update_interval_hours = entry.options.get(
            CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        self.client = KohaClient(
            async_get_clientsession(hass),
            entry.data[CONF_BASE_URL],
            entry.data[CONF_USER_ID],
            entry.data[CONF_PASSWORD],
            self._due_soon_days,
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=(
                timedelta(hours=update_interval_hours)
                if update_interval_hours < DEFAULT_UPDATE_INTERVAL_HOURS
                else None
            ),
        )

        entry.async_on_unload(
            async_track_time_change(
                hass,
                self._async_midnight_update,
                hour=0,
                minute=0,
                second=5,
            )
        )

    async def _async_update_data(self) -> KohaAccountData:
        """Fetch account data from the OPAC."""
        try:
            data = await self.client.async_fetch_account_data(dt_util.now())
            await self._async_apply_progress(data)
            return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CannotConnect as err:
            raise ConfigEntryError(str(err)) from err

    async def _async_midnight_update(self, _now: datetime) -> None:
        """Recalculate due states and fetch fresh data after local midnight."""
        if self.data is not None:
            last_update = self.data.last_update
            recalculated = build_account_data(
                self.data.books,
                self._due_soon_days,
                dt_util.now(),
            )
            recalculated.last_update = last_update
            self._set_progress_counts(recalculated)
            self.async_set_updated_data(recalculated)

        await self.async_request_refresh()

    async def async_load_progress(self) -> None:
        """Load persisted completion state."""
        stored = await self._progress_store.async_load()
        if stored:
            self._completed_items = {
                uid: (
                    value
                    if isinstance(value, str)
                    else value.get("completed_at", "")
                )
                for uid, value in stored.get("completed", {}).items()
            }
            self._archived_items = dict(stored.get("archived", {}))
            self._known_items = dict(stored.get("known", {}))

    def todo_uid(self, book, occurrence: int = 0) -> str:
        """Return a stable identifier for an active checkout."""
        value = "|".join(
            (
                book.title.strip().lower(),
                book.author.strip().lower(),
                book.call_no.strip().lower(),
                book.media_type.strip().lower(),
                str(occurrence),
            )
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    def todo_books(self) -> list[tuple[str, KohaCheckout]]:
        """Return active books with stable Todo identifiers."""
        if self.data is None:
            return []
        return self._todo_books_for(self.data)

    def _todo_books_for(
        self, data: KohaAccountData
    ) -> list[tuple[str, KohaCheckout]]:
        """Return books from account data with stable Todo identifiers."""
        occurrences: dict[tuple[str, str, str, str], int] = {}
        result: list[tuple[str, KohaCheckout]] = []
        for book in data.books:
            key = (book.title, book.author, book.call_no, book.media_type)
            occurrence = occurrences.get(key, 0)
            occurrences[key] = occurrence + 1
            result.append((self.todo_uid(book, occurrence), book))
        return result

    def is_todo_completed(self, uid: str) -> bool:
        """Return whether an active Todo item is completed."""
        return uid in self._completed_items

    def archived_todo_items(self) -> list[tuple[str, dict[str, Any]]]:
        """Return retained completed Todo items."""
        if not self._keep_completed_items:
            return []
        return sorted(
            self._archived_items.items(),
            key=lambda item: item[1].get("completed_at", ""),
            reverse=True,
        )

    async def async_set_todo_completed(self, uid: str, completed: bool) -> None:
        """Persist a Todo item's completion state."""
        if completed:
            self._completed_items[uid] = datetime.now(timezone.utc).isoformat()
        else:
            self._completed_items.pop(uid, None)
            self._archived_items.pop(uid, None)
        await self._async_save_progress()
        if self.data is not None:
            self._set_progress_counts(self.data)
            self.async_set_updated_data(self.data)

    async def _async_apply_progress(self, data: KohaAccountData) -> None:
        """Synchronize active, returned, and retained completed items."""
        active_items = {
            uid: self._book_snapshot(book)
            for uid, book in self._todo_books_for(data)
        }
        active_uids = set(active_items)
        (
            self._completed_items,
            self._archived_items,
            self._known_items,
        ) = synchronize_progress(
            known_items=self._known_items,
            completed_items=self._completed_items,
            archived_items=self._archived_items,
            active_items=active_items,
            complete_returned_items=self._complete_returned_items,
            keep_completed_items=self._keep_completed_items,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        await self._async_save_progress()
        self._set_progress_counts(data, active_uids)

    def _set_progress_counts(
        self, data: KohaAccountData, active_uids: set[str] | None = None
    ) -> None:
        """Set completed and remaining counts on coordinator data."""
        if active_uids is None:
            active_uids = {uid for uid, _book in self.todo_books()}
        data.completed_count, data.remaining_count = progress_counts(
            active_uids, self._completed_items, self._archived_items
        )

    @staticmethod
    def _book_snapshot(book: KohaCheckout) -> dict[str, Any]:
        """Return the Todo fields needed after an item is returned."""
        return {
            "title": book.title,
            "author": book.author,
            "due_iso": book.due_iso,
            "media_type": book.media_type,
            "call_no": book.call_no,
        }

    async def _async_save_progress(self) -> None:
        """Persist progress and checkout snapshots."""
        await self._progress_store.async_save(
            {
                "completed": self._completed_items,
                "archived": self._archived_items,
                "known": self._known_items,
            }
        )
