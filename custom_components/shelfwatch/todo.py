"""Todo platform for ShelfWatch reading progress."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ACCOUNT_NAME, CONF_BASE_URL, DOMAIN
from .coordinator import ShelfWatchCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ShelfWatch Todo list."""
    coordinator: ShelfWatchCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ShelfWatchTodoList(coordinator, entry)])


class ShelfWatchTodoList(
    CoordinatorEntity[ShelfWatchCoordinator], TodoListEntity
):
    """Todo list containing the active checkouts for one account."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM
    _attr_translation_key = "reading_list"

    def __init__(
        self,
        coordinator: ShelfWatchCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Todo list."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_reading_list"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data[CONF_ACCOUNT_NAME],
            "model": "Online-Bibliothekskonto",
            "configuration_url": entry.data[CONF_BASE_URL],
        }
        self._refresh_items()

    def _refresh_items(self) -> None:
        """Build Todo items from the current checkouts."""
        items: list[TodoItem] = []
        for uid, book in self.coordinator.todo_books():
            due: date | datetime | None = None
            if book.due_iso:
                due = datetime.fromisoformat(
                    book.due_iso.replace("Z", "+00:00")
                ).date()
            description_parts = [
                value
                for value in (book.author, book.media_type, book.call_no)
                if value
            ]
            items.append(
                TodoItem(
                    uid=uid,
                    summary=book.title,
                    status=(
                        TodoItemStatus.COMPLETED
                        if self.coordinator.is_todo_completed(uid)
                        else TodoItemStatus.NEEDS_ACTION
                    ),
                    due=due,
                    description=" · ".join(description_parts) or None,
                )
            )
        for uid, archived in self.coordinator.archived_todo_items():
            due: date | datetime | None = None
            if archived.get("due_iso"):
                due = datetime.fromisoformat(
                    archived["due_iso"].replace("Z", "+00:00")
                ).date()
            description_parts = [
                value
                for value in (
                    archived.get("author", ""),
                    archived.get("media_type", ""),
                    archived.get("call_no", ""),
                )
                if value
            ]
            completed = (
                datetime.fromisoformat(archived["completed_at"])
                if archived.get("completed_at")
                else None
            )
            items.append(
                TodoItem(
                    uid=uid,
                    summary=archived.get("title", ""),
                    status=TodoItemStatus.COMPLETED,
                    due=due,
                    description=" · ".join(description_parts) or None,
                    completed=completed,
                )
            )
        self._attr_todo_items = items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update the manually maintained completion status."""
        if item.uid is None or item.status is None:
            return
        await self.coordinator.async_set_todo_completed(
            item.uid, item.status == TodoItemStatus.COMPLETED
        )

    def _handle_coordinator_update(self) -> None:
        """Refresh items when ShelfWatch data or progress changes."""
        self._refresh_items()
        super()._handle_coordinator_update()
