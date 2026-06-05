"""Reading-progress synchronization helpers."""

from __future__ import annotations

from typing import Any


def synchronize_progress(
    *,
    known_items: dict[str, dict[str, Any]],
    completed_items: dict[str, str],
    archived_items: dict[str, dict[str, Any]],
    active_items: dict[str, dict[str, Any]],
    complete_returned_items: bool,
    keep_completed_items: bool,
    completed_at: str,
) -> tuple[
    dict[str, str],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Synchronize active checkouts with completion and history state."""
    completed = dict(completed_items)
    archived = {uid: dict(item) for uid, item in archived_items.items()}
    active_uids = set(active_items)
    returned_uids = set(known_items) - active_uids

    for uid in active_uids & set(archived):
        archived.pop(uid, None)
        completed.pop(uid, None)

    for uid in returned_uids:
        is_completed = uid in completed
        if complete_returned_items and not is_completed:
            completed[uid] = completed_at
            is_completed = True

        if is_completed and keep_completed_items:
            snapshot = dict(known_items[uid])
            snapshot["completed_at"] = completed[uid]
            snapshot["returned"] = True
            archived[uid] = snapshot
        else:
            completed.pop(uid, None)
            archived.pop(uid, None)

    if not keep_completed_items:
        archived.clear()
        for uid in set(completed) - active_uids:
            completed.pop(uid, None)

    return completed, archived, dict(active_items)


def progress_counts(
    active_uids: set[str],
    completed_items: dict[str, str],
    archived_items: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    """Return completed and remaining media counts."""
    active_completed = len(active_uids & set(completed_items))
    return active_completed + len(archived_items), len(active_uids) - active_completed
