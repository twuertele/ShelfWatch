"""Config flow for ShelfWatch."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import SectionConfig, section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_ACCOUNT_NAME,
    CONF_BASE_URL,
    CONF_COMPLETE_RETURNED_ITEMS,
    CONF_DUE_SOON_DAYS,
    CONF_ENABLE_TODO_LIST,
    CONF_KEEP_COMPLETED_ITEMS,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL_HOURS,
    CONF_USER_ID,
    DEFAULT_BASE_URL,
    DEFAULT_COMPLETE_RETURNED_ITEMS,
    DEFAULT_DUE_SOON_DAYS,
    DEFAULT_ENABLE_TODO_LIST,
    DEFAULT_KEEP_COMPLETED_ITEMS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)
from .koha_client import CannotConnect, InvalidAuth, KohaClient, normalize_base_url
from .settings import (
    CONF_DUE_DATES_AND_UPDATES,
    CONF_READING_PROGRESS,
    normalize_options_input,
)


def _entry_unique_id(base_url: str, user_id: str) -> str:
    """Create a stable non-readable unique ID for one account/base URL."""
    normalized = f"{normalize_base_url(base_url).lower()}|{user_id.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user setup schema."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_ACCOUNT_NAME,
                default=user_input.get(CONF_ACCOUNT_NAME, ""),
            ): str,
            vol.Required(
                CONF_BASE_URL,
                default=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            ): str,
            vol.Required(
                CONF_USER_ID,
                default=user_input.get(CONF_USER_ID, ""),
            ): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


def _options_schema(options: dict[str, Any]) -> vol.Schema:
    """Return the options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_DUE_DATES_AND_UPDATES): section(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_DUE_SOON_DAYS,
                            default=options.get(
                                CONF_DUE_SOON_DAYS,
                                DEFAULT_DUE_SOON_DAYS,
                            ),
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=0,
                                max=60,
                                mode=NumberSelectorMode.BOX,
                                step=1,
                            )
                        ),
                        vol.Required(
                            CONF_UPDATE_INTERVAL_HOURS,
                            default=options.get(
                                CONF_UPDATE_INTERVAL_HOURS,
                                DEFAULT_UPDATE_INTERVAL_HOURS,
                            ),
                        ): NumberSelector(
                            NumberSelectorConfig(
                                min=1,
                                max=24,
                                mode=NumberSelectorMode.BOX,
                                step=1,
                            )
                        ),
                    }
                ),
                SectionConfig(collapsed=False),
            ),
            vol.Required(CONF_READING_PROGRESS): section(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_ENABLE_TODO_LIST,
                            default=options.get(
                                CONF_ENABLE_TODO_LIST,
                                DEFAULT_ENABLE_TODO_LIST,
                            ),
                        ): BooleanSelector(),
                        vol.Required(
                            CONF_COMPLETE_RETURNED_ITEMS,
                            default=options.get(
                                CONF_COMPLETE_RETURNED_ITEMS,
                                DEFAULT_COMPLETE_RETURNED_ITEMS,
                            ),
                        ): BooleanSelector(),
                        vol.Required(
                            CONF_KEEP_COMPLETED_ITEMS,
                            default=options.get(
                                CONF_KEEP_COMPLETED_ITEMS,
                                DEFAULT_KEEP_COMPLETED_ITEMS,
                            ),
                        ): BooleanSelector(),
                    }
                ),
                SectionConfig(collapsed=False),
            ),
        }
    )


async def _validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> None:
    """Validate OPAC credentials."""
    client = KohaClient(
        async_get_clientsession(hass),
        user_input[CONF_BASE_URL],
        user_input[CONF_USER_ID],
        user_input[CONF_PASSWORD],
    )
    await client.async_validate_login()


class ShelfWatchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ShelfWatch."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ShelfWatchOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_BASE_URL] = normalize_base_url(user_input[CONF_BASE_URL])
            await self.async_set_unique_id(
                _entry_unique_id(user_input[CONF_BASE_URL], user_input[CONF_USER_ID])
            )
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_ACCOUNT_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication when credentials stop working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Ask the user for fresh credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        current_data = dict(reauth_entry.data)

        if user_input is not None:
            updated_data = {
                **current_data,
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                await _validate_input(self.hass, updated_data)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )


class ShelfWatchOptionsFlow(config_entries.OptionsFlow):
    """Handle ShelfWatch options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage ShelfWatch options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=normalize_options_input(user_input),
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self._config_entry.options)),
        )
