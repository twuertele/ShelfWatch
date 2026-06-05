# ShelfWatch

![ShelfWatch icon](custom_components/shelfwatch/brand/logo.png)

ShelfWatch is a Home Assistant custom integration for Koha / LMSCloud library accounts.

It logs in to the OPAC account page, reads the current checkouts from the HTML account view, and exposes due dates, counts, status, and checkout details as Home Assistant sensors.

## Features

- UI setup through Home Assistant config flow
- One Home Assistant config entry per library account
- Koha / LMSCloud OPAC HTML login and scraping
- Current checkout count
- Next due date
- Days until the next due date
- Due today, due soon, and overdue counts
- Full borrowed media list in sensor attributes
- Optional native Home Assistant Todo list for reading progress
- Optional completed and remaining media sensors
- German and English Home Assistant translations
- Reauthentication when stored credentials are rejected

## Why HTML Scraping?

ShelfWatch intentionally does not use the Koha REST API for this MVP.

For the tested LMSCloud OPAC, simple end-user API authentication is not suitable: Basic auth is disabled, and the OPAC account page does not use browser-side `/api/` calls for the checkout data needed here.

Each account is refreshed during setup/startup and shortly after local
midnight. The interval can be configured per account from 1 to 24 hours, with
24 hours as the default. Relative due-date values are recalculated at the local
day change before the network refresh completes.

The account options can enable a native Home Assistant Todo list. Current
checkouts are synchronized automatically, manually completed items are stored
locally, and returned items disappear from the active list. Further options
can mark returned media completed and retain completed entries as reading
history.

ShelfWatch therefore uses the same login form as a browser and parses the account page HTML.

## Installation With HACS

Until ShelfWatch is available as a default HACS repository:

1. Open HACS.
2. Open the three-dot menu.
3. Choose **Custom repositories**.
4. Add the ShelfWatch GitHub repository URL.
5. Select category **Integration**.
6. Install **ShelfWatch**.
7. Restart Home Assistant.

## Setup

After restarting Home Assistant:

1. Go to **Settings** -> **Devices & services**.
2. Select **Add integration**.
3. Search for **ShelfWatch**.
4. Enter:
   - account name
   - OPAC base URL
   - user ID
   - password
5. Submit the form.

The account name is a free display name. Use something that describes the person or library card, for example a child's name.

Example OPAC base URL:

```text
https://sb-muehlacker.lmscloud.net
```

ShelfWatch validates the login before creating the config entry.

## Options

Open **Settings** -> **Devices & services** -> **ShelfWatch** -> **Configure** to adjust account-specific options.

Available options:

- **Due dates and updates**
  - due soon threshold in days, default `7`
  - update interval in hours, default `24`
- **Reading progress and Todo list**
  - optional reading-progress Todo list
  - optionally mark returned media as completed
  - optionally retain completed entries as reading history

The Home Assistant options dialog explains each setting. Return handling
requires the Todo list, and retained history requires automatic completion of
returned media.

## Sensors

ShelfWatch creates these sensors per configured account:

- checkouts
- next due date
- days until next due date
- overdue
- due today
- due soon
- status
- books
- last update

The books sensor and grouped due-state sensors expose detailed media lists in attributes. Home Assistant entity states stay small, while dashboards and automations can still use the full checkout detail data.

Example attributes:

```yaml
status: "ok"
next_due_date: "2026-06-10"
next_due_iso: "2026-06-10T23:59:00Z"
next_due_in_days: 6
overdue_count: 0
due_today_count: 0
due_soon_count: 0
last_update: "2026-06-04T15:30:00Z"
books:
  - title: "Example Book"
    author: "Example Author"
    due_text: "10/06/2026"
    due_iso: "2026-06-10T23:59:00Z"
    due_in_days: 6
    media_type: "Book"
    call_no: "A 123"
    renewal_info: "Renewable"
overdue_books: []
due_today_books: []
due_soon_books: []
```

Status values:

- `empty`: no current checkouts
- `ok`: checkouts exist, but none are due soon
- `due_soon`: at least one checkout is due within the configured window
- `due_today`: at least one checkout is due today
- `overdue`: at least one checkout is overdue

## Known HTML Dependency

ShelfWatch currently depends on the tested Koha / LMSCloud checkout table structure:

- checkout table: `#checkoutst tbody`
- title per row: `td.title .biblio-title`
- author per row: `td.author`
- due date per row: `td.date_due`
- machine-readable due date: `td.date_due[data-order]` with `YYYY-MM-DD HH:MM:SS`
- optional media type: `td.itype`
- optional call number: `td.call_no`
- optional renewal info: `td.renew`

If the OPAC theme or markup changes, parsing may need adjustment.

## Privacy

ShelfWatch stores credentials in the Home Assistant config entry storage, like other config-flow based integrations.

It does not send checkout data to a third-party service. Data is fetched directly from the configured OPAC base URL.

## Current Limitations

- Renewal actions are not implemented yet.
- The due-soon threshold defaults to 7 days and can be changed per account in the integration options.
- The automatic update interval defaults to 24 hours and can be changed per account from 1 to 24 hours.
- Reading-progress Todo lists are optional. They include current checkouts and
  can retain completed returned media when history is enabled.
- HTML parsing is tailored to the tested Koha / LMSCloud OPAC markup.

## Planned Features

- Improve the borrowed-media list outside dashboards.
- Research a calendar entity for due dates.
- Visually distinguish manually and automatically completed Todo items.
- Use stable OPAC item identifiers if they become available in the HTML.
- Research wishlist and renewal support.
