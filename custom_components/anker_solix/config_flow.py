"""Adds config flow for Anker Solix."""
from __future__ import annotations

import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_COUNTRY_CODE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from . import api_client
from .const import (
    ACCEPT_TERMS,
    ALLOW_TESTMODE,
    DOMAIN,
    ERROR_DETAIL,
    EXAMPLESFOLDER,
    INTERVALMULT,
    LOGGER,
    SHARED_ACCOUNT,
    TC_LINK,
    TERMS_LINK,
    TESTFOLDER,
    TESTMODE,
)

SCAN_INTERVAL_DEF = 60
INTERVALMULT_DEF = 10  # multiplier for scan interval

_SCAN_INTERVAL_MIN = 10 if ALLOW_TESTMODE else 30
_SCAN_INTERVAL_MAX = 600
_SCAN_INTERVAL_STEP = 10
_INTERVALMULT_MIN = 1
_INTERVALMULT_MAX = 30
_INTERVALMULT_STEP = 1
_ALLOW_TESTMODE = bool(ALLOW_TESTMODE)


class AnkerSolixFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Anker Solix."""

    VERSION = 1

    def __init__(self) -> None:
        """Init the FlowHandler."""
        super().__init__()
        self._data: dict[str, Any] = {}
        self.client: api_client.AnkerSolixApiClient = None
        self.testmode: bool = False
        self.testfolder: str = None
        self.examplesfolder: str = os.path.join(
            os.path.dirname(__file__), EXAMPLESFOLDER
        )
        # ensure folder for example json folders exists
        os.makedirs(self.examplesfolder, exist_ok=True)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AnkerSolixOptionsFlowHandler:
        """Get the options flow for this handler."""
        return AnkerSolixOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        cfg_schema = {
            vol.Required(
                CONF_USERNAME,
                default=(user_input or {}).get(CONF_USERNAME),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.EMAIL, autocomplete="username"
                )
            ),
            vol.Required(
                CONF_PASSWORD,
                default=(user_input or {}).get(CONF_PASSWORD),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                ),
            ),
            vol.Required(
                CONF_COUNTRY_CODE,
                default=(user_input or {}).get(CONF_COUNTRY_CODE)
                or self.hass.config.country,
            ): selector.CountrySelector(
                selector.CountrySelectorConfig(),
            ),
            vol.Required(
                ACCEPT_TERMS,
                default=(user_input or {}).get(ACCEPT_TERMS, False),
            ): selector.BooleanSelector(),
        }
        placeholders[TERMS_LINK] = TC_LINK

        if user_input:
            if not user_input.get(ACCEPT_TERMS, ""):
                # Terms not accepted
                errors[ACCEPT_TERMS] = ACCEPT_TERMS
            else:
                account_user = user_input.get(CONF_USERNAME, "")
                try:
                    if await self.async_set_unique_id(account_user.lower()):
                        # abort if username already setup
                        self._abort_if_unique_id_configured()
                    else:
                        self.client = await self._authenticate_client(
                            username=account_user,
                            password=user_input.get(CONF_PASSWORD),
                            countryid=user_input.get(CONF_COUNTRY_CODE),
                        )
                except api_client.AnkerSolixApiClientAuthenticationError as exception:
                    LOGGER.warning(exception)
                    errors["base"] = "auth"
                    placeholders[ERROR_DETAIL] = str(exception)
                except api_client.AnkerSolixApiClientCommunicationError as exception:
                    LOGGER.error(exception)
                    errors["base"] = "connection"
                    placeholders[ERROR_DETAIL] = str(exception)
                except api_client.AnkerSolixApiClientRetryExceededError as exception:
                    LOGGER.exception(exception)
                    errors["base"] = "exceeded"
                    placeholders[ERROR_DETAIL] = str(exception)
                except api_client.AnkerSolixApiClientError as exception:
                    LOGGER.exception(exception)
                    errors["base"] = "unknown"
                    placeholders[ERROR_DETAIL] = str(exception)

                # get first site data for account and verify nothing is shared with existing configuration
                await self.client.api.update_sites()
                if cfg_entry := await async_check_and_remove_devices(self.hass, user_input, self.client.api.sites | self.client.api.devices):
                    errors[CONF_USERNAME] = "duplicate_devices"
                    placeholders[CONF_USERNAME] = str(account_user)
                    placeholders[SHARED_ACCOUNT] = str(cfg_entry.title)
                else:
                    self._data = user_input
                    # add some fixed configuration data
                    self._data[EXAMPLESFOLDER] = self.examplesfolder

                    # set initial options for entry
                    options = {
                        CONF_SCAN_INTERVAL: SCAN_INTERVAL_DEF,
                        INTERVALMULT: INTERVALMULT_DEF,
                    }

                    return self.async_create_entry(
                        title=self.client.api.nickname
                        if self.client and self.client.api
                        else self._data.get(CONF_USERNAME),
                        data=self._data,
                        options=options,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(cfg_schema),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _authenticate_client(
        self, username: str, password: str, countryid: str
    ) -> api_client.AnkerSolixApiClient:
        """Validate credentials and return the api client."""
        client = api_client.AnkerSolixApiClient(
            username=username,
            password=password,
            countryid=countryid,
            session=async_create_clientsession(self.hass),
        )
        await client.authenticate()
        return client


class AnkerSolixOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle options flow."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}   # NOTE: Passed option placeholder do not work with translation files, HASS Bug?

        if not (jsonfolders := api_client.json_example_folders()):
            # Add empty element to ensure proper list validation
            jsonfolders = [""]

        if user_input:
            if user_input.get(TESTFOLDER) or not user_input.get(TESTMODE):
                return self.async_create_entry(title="", data=user_input)
            # Test mode enabled but no existing folder selected
            errors[TESTFOLDER] = "folder_invalid"

        opt_schema = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=(user_input or self.config_entry.options).get(
                    CONF_SCAN_INTERVAL,
                    SCAN_INTERVAL_DEF,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_SCAN_INTERVAL_MIN,
                    max=_SCAN_INTERVAL_MAX,
                    step=_SCAN_INTERVAL_STEP,
                    unit_of_measurement="sec",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                INTERVALMULT,
                default=(user_input or self.config_entry.options).get(
                    INTERVALMULT, INTERVALMULT_DEF
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_INTERVALMULT_MIN,
                    max=_INTERVALMULT_MAX,
                    step=_INTERVALMULT_STEP,
                    unit_of_measurement="updates",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        }
        if _ALLOW_TESTMODE:
            opt_schema.update(
                {
                    vol.Optional(
                        TESTMODE,
                        default=(user_input or self.config_entry.options).get(
                            TESTMODE, False
                        ),
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        TESTFOLDER,
                        description={
                            "suggested_value": (
                                user_input or self.config_entry.options
                            ).get(
                                TESTFOLDER,
                                jsonfolders[0] if len(jsonfolders) > 0 else "",
                            )
                        },
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=jsonfolders, mode="dropdown", sort=True
                        )
                    ),
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(opt_schema),
            errors=errors,
            description_placeholders=placeholders,
        )


async def async_check_and_remove_devices(
    hass: HomeAssistant, user_input: dict, apidata: dict
) -> config_entries.ConfigEntry | None:
    """Check if given user input with its initial apidata has shared devices with existing configuration.

    If there are none, remove devices of this config that are no longer available for the configuration.
    """

    obsolete_user_devs = {}
    # get all device entries for a domain
    cfg_entries = hass.config_entries.async_entries(domain=DOMAIN)
    for cfg_entry in cfg_entries:
        device_entries = dr.async_entries_for_config_entry(dr.async_get(hass), cfg_entry.entry_id)
        for dev_entry in device_entries:
            if (
                username := str(user_input.get(CONF_USERNAME) or "").lower()
            ) and username != cfg_entry.unique_id:
                # config entry of another account
                if dev_entry.serial_number in apidata:
                    return cfg_entry
            # device is registered for same account, check if still used in coordinator data and add to obsolete list for removal
            elif dev_entry.serial_number not in apidata:
                obsolete_user_devs[dev_entry.id] = dev_entry.serial_number

    # Remove the obsolete device entries
    dev_registry = None
    for dev_id, serial in obsolete_user_devs.items():
        # ensure to obtain dev registry again if no longer available
        if dev_registry is None:
            dev_registry = dr.async_get(hass)
        dev_registry.async_remove_device(dev_id)
        # NOTE: removal of any underlying entities is handled by core
        LOGGER.info(
            "Removed device entry %s from registry for unused configuration entry device %s",
            dev_id,
            serial,
        )
    return None
