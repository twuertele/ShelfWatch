"""Async Koha/LMSCloud OPAC client for ShelfWatch."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

DATE_ORDER_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGIN_PATH = "/cgi-bin/koha/opac-user.pl"


class KohaClientError(Exception):
    """Base exception for Koha client errors."""


class InvalidAuth(KohaClientError):
    """Raised when Koha rejects the supplied credentials."""


class CannotConnect(KohaClientError):
    """Raised when the OPAC cannot be reached."""


@dataclass
class KohaCheckout:
    """A single OPAC checkout row."""

    title: str
    author: str
    due_text: str
    due_iso: str | None
    due_in_days: int | None
    media_type: str
    call_no: str
    renewal_info: str

    def as_dict(self) -> dict[str, Any]:
        """Return a Home Assistant attribute-friendly dict."""
        return {
            "title": self.title,
            "author": self.author,
            "due_text": self.due_text,
            "due_iso": self.due_iso,
            "due_in_days": self.due_in_days,
            "media_type": self.media_type,
            "call_no": self.call_no,
            "renewal_info": self.renewal_info,
        }


@dataclass
class KohaAccountData:
    """Parsed account data for one library account."""

    checkout_count: int
    status: str
    next_due_date: str | None
    next_due_iso: str | None
    next_due_in_days: int | None
    overdue_count: int
    due_soon_count: int
    due_today_count: int
    last_update: str
    books: list[KohaCheckout]
    overdue_books: list[KohaCheckout]
    due_today_books: list[KohaCheckout]
    due_soon_books: list[KohaCheckout]
    completed_count: int = 0
    remaining_count: int = 0


def normalize_base_url(base_url: str) -> str:
    """Normalize an OPAC base URL."""
    return base_url.strip().rstrip("/")


def login_url_for_base(base_url: str) -> str:
    """Build the OPAC account/login URL from a base URL."""
    return urljoin(f"{normalize_base_url(base_url)}/", LOGIN_PATH.lstrip("/"))


def clean_text(value: str | None) -> str:
    """Collapse whitespace in scraped text."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def cell_text(row: Any, selector: str) -> str:
    """Return text from a table cell selector."""
    element = row.select_one(selector)
    return clean_text(element.get_text(" ", strip=True)) if element else ""


def parse_due_datetime(value: str) -> datetime | None:
    """Parse Koha's data-order due date."""
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_ORDER_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        _LOGGER.warning("Could not parse Koha due date from data-order=%r", value)
        return None


def iso_or_none(value: datetime | None) -> str | None:
    """Return an ISO string with Z suffix."""
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def days_until(due_date: datetime | None, now: datetime) -> int | None:
    """Return calendar days until a due date."""
    if due_date is None:
        return None
    return (due_date.date() - now.date()).days


def login_likely_failed(html: str) -> bool:
    """Detect common OPAC login failure pages."""
    soup = BeautifulSoup(html, "html.parser")
    login_form = soup.select_one(
        "form#auth, form[action*='opac-user.pl'] input[name='userid'], "
        "form[action*='opac-user.pl'] input[name='login_userid']"
    )
    page_text = clean_text(soup.get_text(" ", strip=True)).lower()
    failure_terms = (
        "invalid userid",
        "invalid password",
        "login incorrect",
        "login failed",
        "authentication failed",
        "please log in",
        "log in to your account",
        "anmeldung fehlgeschlagen",
        "ungültige benutzerkennung",
        "ungültiges passwort",
        "benutzerkennung oder passwort ist falsch",
        "benutzerkennung/passwort ist falsch",
    )
    return bool(login_form) and any(term in page_text for term in failure_terms)


def parse_checkouts(html: str, now: datetime) -> list[KohaCheckout]:
    """Parse checkout rows from the Koha OPAC account page."""
    soup = BeautifulSoup(html, "html.parser")
    checkout_body = soup.select_one("#checkoutst tbody")
    if checkout_body is None:
        _LOGGER.debug("No checkout table found; treating account as empty")
        return []

    checkouts: list[KohaCheckout] = []
    for row in checkout_body.select("tr"):
        title = cell_text(row, "td.title .biblio-title")
        if not title:
            continue

        due_cell = row.select_one("td.date_due")
        due_text = clean_text(due_cell.get_text(" ", strip=True)) if due_cell else ""
        due_raw = str(due_cell.get("data-order", "")) if due_cell else ""
        due_datetime = parse_due_datetime(due_raw)

        checkouts.append(
            KohaCheckout(
                title=title,
                author=cell_text(row, "td.author"),
                due_text=due_text,
                due_iso=iso_or_none(due_datetime),
                due_in_days=days_until(due_datetime, now),
                media_type=cell_text(row, "td.itype"),
                call_no=cell_text(row, "td.call_no"),
                renewal_info=cell_text(row, "td.renew"),
            )
        )

    return sorted(
        checkouts,
        key=lambda checkout: (
            checkout.due_iso is None,
            checkout.due_iso or "",
            checkout.title.lower(),
        ),
    )


def build_account_data(
    checkouts: list[KohaCheckout],
    due_soon_days: int,
    now: datetime,
) -> KohaAccountData:
    """Build aggregate account data from parsed checkouts."""
    for checkout in checkouts:
        due_datetime = (
            datetime.fromisoformat(checkout.due_iso.replace("Z", "+00:00"))
            if checkout.due_iso
            else None
        )
        checkout.due_in_days = days_until(due_datetime, now)

    due_values = [
        datetime.fromisoformat(checkout.due_iso.replace("Z", "+00:00"))
        for checkout in checkouts
        if checkout.due_iso
    ]
    next_due = min(due_values) if due_values else None

    overdue_books = [
        checkout
        for checkout in checkouts
        if checkout.due_in_days is not None and checkout.due_in_days < 0
    ]
    due_today_books = [
        checkout for checkout in checkouts if checkout.due_in_days == 0
    ]
    due_soon_books = [
        checkout
        for checkout in checkouts
        if checkout.due_in_days is not None
        and 0 <= checkout.due_in_days <= due_soon_days
    ]

    if overdue_books:
        status = "overdue"
    elif due_today_books:
        status = "due_today"
    elif due_soon_books:
        status = "due_soon"
    elif checkouts:
        status = "ok"
    else:
        status = "empty"

    return KohaAccountData(
        checkout_count=len(checkouts),
        status=status,
        next_due_date=next_due.date().isoformat() if next_due else None,
        next_due_iso=iso_or_none(next_due),
        next_due_in_days=days_until(next_due, now),
        overdue_count=len(overdue_books),
        due_soon_count=len(due_soon_books),
        due_today_count=len(due_today_books),
        last_update=iso_or_none(now) or "",
        books=checkouts,
        overdue_books=overdue_books,
        due_today_books=due_today_books,
        due_soon_books=due_soon_books,
    )


class KohaClient:
    """Small async client for one Koha/LMSCloud OPAC account."""

    def __init__(
        self,
        session: Any,
        base_url: str,
        user_id: str,
        password: str,
        due_soon_days: int = 7,
    ) -> None:
        self._session = session
        self._base_url = normalize_base_url(base_url)
        self._login_url = login_url_for_base(self._base_url)
        self._user_id = user_id
        self._password = password
        self._due_soon_days = due_soon_days

    async def async_validate_login(self) -> None:
        """Validate credentials by performing a login."""
        await self._async_login()

    async def async_fetch_account_data(
        self, now: datetime | None = None
    ) -> KohaAccountData:
        """Log in, fetch the account page, and parse current checkouts."""
        now = now or datetime.now(timezone.utc)
        html = await self._async_login()
        html = await self._async_get_account_page()

        if login_likely_failed(html):
            raise InvalidAuth("OPAC session is no longer authenticated")

        return build_account_data(parse_checkouts(html, now), self._due_soon_days, now)

    async def _async_login(self) -> str:
        """Log into the OPAC account page."""
        from aiohttp import ClientError, ClientResponseError

        try:
            async with self._session.get(self._login_url, timeout=30) as response:
                response.raise_for_status()
                login_page = await response.text()

            soup = BeautifulSoup(login_page, "html.parser")
            form = soup.select_one("form[action*='opac-user.pl']")
            if form is None:
                raise CannotConnect("OPAC login form was not found")

            form_fields = {
                element["name"]: element.get("value", "")
                for element in form.select("input[name]")
                if element.get("type") not in {"button", "file", "image", "submit"}
            }
            user_field = next(
                (
                    field
                    for field in ("login_userid", "userid")
                    if field in form_fields
                ),
                None,
            )
            password_field = next(
                (
                    field
                    for field in ("login_password", "password")
                    if field in form_fields
                ),
                None,
            )
            if user_field is None or password_field is None:
                raise CannotConnect("OPAC login form fields were not recognized")

            form_fields[user_field] = self._user_id
            form_fields[password_field] = self._password
            form_action = urljoin(
                str(response.url), form.get("action") or self._login_url
            )

            async with self._session.post(
                form_action,
                data=form_fields,
                headers={"Referer": str(response.url)},
                timeout=30,
            ) as response:
                response.raise_for_status()
                html = await response.text()
        except (ClientError, ClientResponseError, TimeoutError) as err:
            raise CannotConnect(f"Could not connect to OPAC: {err}") from err

        if login_likely_failed(html):
            raise InvalidAuth("OPAC rejected the supplied credentials")

        return html

    async def _async_get_account_page(self) -> str:
        """Fetch the OPAC account page after login."""
        from aiohttp import ClientError, ClientResponseError

        try:
            async with self._session.get(self._login_url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()
        except (ClientError, ClientResponseError, TimeoutError) as err:
            raise CannotConnect(f"Could not fetch OPAC account page: {err}") from err
