"""Adds config flow for Anker Solix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from awesomeversion import AwesomeVersion
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_COUNTRY_CODE,
    CONF_DELAY_TIME,
    CONF_EXCLUDE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    __version__ as HAVERSION,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    restore_state,
    selector,
)
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from . import api_client
from .const import (
    ACCEPT_TERMS,
    ALLOW_TESTMODE,
    CONF_API_OPTIONS,
    CONF_ENDPOINT_LIMIT,
    CONF_MQTT_OPTIONS,
    CONF_MQTT_TEST_SPEED,
    CONF_MQTT_USAGE,
    CONF_SKIP_INVALID,
    CONF_TEST_OPTIONS,
    CONF_TRIGGER_TIMEOUT,
    DOMAIN,
    ERROR_DETAIL,
    EXAMPLESFOLDER,
    INTERVALMULT,
    LOGGER,
    MQ_LINK,
    MQTT_LINK,
    SHARED_ACCOUNT,
    TC_LINK,
    TERMS_LINK,
    TESTFOLDER,
    TESTMODE,
)
from .solixapi.apitypes import ApiCategories, SolixDeviceType

# Define integration configuration entry versions
CONFIG_VERSION = 2
CONFIG_MINOR_VERSION = 1

# Define integration option limits and defaults
SCAN_INTERVAL_DEF: int = api_client.DEFAULT_UPDATE_INTERVAL
INTERVALMULT_DEF: int = api_client.DEFAULT_DEVICE_MULTIPLIER
DELAY_TIME_DEF: float = api_client.DEFAULT_DELAY_TIME
TIMEOUT_DEF: int = api_client.DEFAULT_TIMEOUT
TRIGGER_TIMEOUT_DEF: int = api_client.DEFAULT_TRIGGER_TIMEOUT
ENDPOINT_LIMIT_DEF: int = api_client.DEFAULT_ENDPOINT_LIMIT
SKIP_INVALID_DEF: bool = False
MQTT_USAGE_DEF: bool = api_client.DEFAULT_MQTT_USAGE

_SCAN_INTERVAL_MIN: int = 10 if ALLOW_TESTMODE else 30
_SCAN_INTERVAL_MAX: int = 600
_SCAN_INTERVAL_STEP: int = 10
_INTERVALMULT_MIN: int = 2
_INTERVALMULT_MAX: int = 60
_INTERVALMULT_STEP: int = 2
_DELAY_TIME_MIN: float = api_client.SolixDefaults.REQUEST_DELAY_MIN
_DELAY_TIME_MAX: float = 2.0
_DELAY_TIME_STEP: float = 0.1
_TIMEOUT_MIN: int = api_client.SolixDefaults.REQUEST_TIMEOUT_MIN
_TIMEOUT_MAX: int = api_client.SolixDefaults.REQUEST_TIMEOUT_MAX
_TIMEOUT_STEP: int = 1
_ENDPOINT_LIMIT_MIN: int = 0
_ENDPOINT_LIMIT_MAX: int = 30
_ENDPOINT_LIMIT_STEP: int = 1
_ALLOW_TESTMODE: bool = bool(ALLOW_TESTMODE)
_ACCEPT_TERMS: bool = False
_TRIGGER_TIMEOUT_MIN: int = api_client.SolixDefaults.TRIGGER_TIMEOUT_MIN
_TRIGGER_TIMEOUT_MAX: int = api_client.SolixDefaults.TRIGGER_TIMEOUT_MAX
_TRIGGER_TIMEOUT_STEP: int = 10
_MQTT_POLLER_SPEED: float = 1
_MQTT_POLLER_SPEED_MIN: float = 0.25
_MQTT_POLLER_SPEED_MAX: float = 10
_MQTT_POLLER_SPEED_DEF: float = 1


class AnkerSolixFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Anker Solix."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self) -> None:
        """Init the FlowHandler."""
        super().__init__()
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self.client: api_client.AnkerSolixApiClient = None
        self.testmode: bool = False
        self.testfolder: str = None
        self.examplesfolder: str = str(Path(__file__).parent / EXAMPLESFOLDER)
        # ensure folder for example json folders exists
        Path(self.examplesfolder).mkdir(parents=True, exist_ok=True)

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

        cfg_schema = await self.get_config_schema(user_input or self._data)
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
                        self.client = await self._authenticate_client(user_input)

                    # get first site data for account and verify nothing is shared with existing configuration
                    await self.client.api.update_sites()
                    if cfg_entry := await async_check_and_remove_devices(
                        self.hass,
                        user_input,
                        self.client.api.getCaches(),
                    ):
                        errors[CONF_USERNAME] = "duplicate_devices"
                        placeholders[CONF_USERNAME] = str(account_user)
                        placeholders[SHARED_ACCOUNT] = str(cfg_entry.title)
                    else:
                        self._data = user_input
                        # add some fixed configuration data
                        self._data[EXAMPLESFOLDER] = self.examplesfolder
                        self._data["nickname"] = (
                            self.client.api.apisession.nickname or ""
                        )

                        # next step to configure initial options
                        return await self.async_step_user_options(user_options=None)

                except api_client.AnkerSolixApiClientAuthenticationError as exception:
                    LOGGER.warning(exception)
                    errors["base"] = "auth"
                    placeholders[ERROR_DETAIL] = str(exception)
                except api_client.AnkerSolixApiClientCommunicationError as exception:
                    LOGGER.error(exception)
                    errors["base"] = "connection"
                    placeholders[ERROR_DETAIL] = str(exception)
                except api_client.AnkerSolixApiClientRetryExceededError as exception:
                    LOGGER.error(exception)
                    errors["base"] = "exceeded"
                    placeholders[ERROR_DETAIL] = str(exception)
                except (api_client.AnkerSolixApiClientError, Exception) as exception:  # pylint: disable=broad-except  # noqa: BLE001
                    LOGGER.error(exception)
                    errors["base"] = "unknown"
                    placeholders[ERROR_DETAIL] = (
                        f"Exception {type(exception)}: {exception}"
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(cfg_schema),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Perform reauthentication upon an API authentication error."""

        return await self.async_step_reauth_confirm()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add reconfigure step to allow to reconfigure a config entry."""

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Confirm reauthentication dialog."""

        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        config_entry: config_entries.ConfigEntry = (
            self.hass.config_entries.async_get_entry(self.context.get("entry_id"))
        )
        # get existing config data as dict
        self._data = config_entry.data.copy()
        cfg_schema = await self.get_config_schema(user_input or self._data)
        placeholders[TERMS_LINK] = TC_LINK

        if user_input:
            if not user_input.get(ACCEPT_TERMS, ""):
                # Terms not accepted
                errors[ACCEPT_TERMS] = ACCEPT_TERMS
            else:
                account_user = user_input.get(CONF_USERNAME, "")
                try:
                    # Obtain and cache authentication token for entered user
                    client = await self._authenticate_client(user_input)
                    # set testmode for client and json test file folder for api
                    testmode = config_entry.options.get(CONF_TEST_OPTIONS, {}).get(
                        TESTMODE, False
                    )
                    testfolder = config_entry.options.get(CONF_TEST_OPTIONS, {}).get(
                        TESTFOLDER
                    )
                    if testmode and testfolder:
                        # set json test file folder for api to be validated
                        client.api.testDir(
                            str(Path(self._data.get(EXAMPLESFOLDER, "")) / testfolder)
                        )
                    # get first site data for account and verify nothing is shared with existing configuration
                    await client.api.update_sites(fromFile=(testfolder and testmode))
                    if cfg_entry := await async_check_and_remove_devices(
                        hass=self.hass,
                        user_input=user_input,
                        apidata=client.api.getCaches(),
                        configured_user=self._data.get(CONF_USERNAME),
                    ):
                        errors[CONF_USERNAME] = "duplicate_devices"
                        placeholders[CONF_USERNAME] = str(account_user)
                        placeholders[SHARED_ACCOUNT] = str(cfg_entry.title)
                    else:
                        # ensure removal of existing devices prior reload
                        await async_check_and_remove_devices(
                            hass=self.hass,
                            user_input=self._data,
                            apidata={},
                        )
                        # update fields of configuration flow
                        self._data.update(user_input)
                        self._data["nickname"] = client.api.apisession.nickname or ""
                        self.client = client
                        # update existing config entry
                        return self.async_update_reload_and_abort(
                            entry=config_entry,
                            unique_id=account_user,
                            title=self.client.api.apisession.nickname
                            if self.client and self.client.api
                            else account_user,
                            data=self._data,
                            # options=config_entry.options.copy(),
                            reason="reconfig_successful",
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
                    LOGGER.error(exception)
                    errors["base"] = "exceeded"
                    placeholders[ERROR_DETAIL] = str(exception)
                except (api_client.AnkerSolixApiClientError, Exception) as exception:  # pylint: disable=broad-except  # noqa: BLE001
                    LOGGER.error(exception)
                    errors["base"] = "unknown"
                    placeholders[ERROR_DETAIL] = (
                        f"Exception {type(exception)}: {exception}"
                    )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(cfg_schema),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_user_options(
        self, user_options: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        placeholders[MQTT_LINK] = MQ_LINK

        if user_options:
            self._options = user_options
            test_options = user_options.get(CONF_TEST_OPTIONS, {})
            if test_options.get(TESTFOLDER) or not test_options.get(TESTMODE):
                return self.async_create_entry(
                    title=self.client.api.apisession.nickname
                    if self.client and self.client.api
                    else self._data.get(CONF_USERNAME),
                    data=self._data,
                    options=self._options,
                    description_placeholders=placeholders,
                )
            # Test mode enabled but no existing folder selected
            errors[TESTFOLDER] = "folder_invalid"

        return self.async_show_form(
            step_id="user_options",
            data_schema=vol.Schema(
                await get_options_schema(user_options or self._options)
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def _authenticate_client(
        self, user_input: dict
    ) -> api_client.AnkerSolixApiClient:
        """Validate credentials and return the api client."""
        client = api_client.AnkerSolixApiClient(
            user_input,
            session=async_create_clientsession(self.hass),
        )
        await client.authenticate(restart=True)
        return client

    async def get_config_schema(self, entry: dict | None = None) -> dict:
        """Create the config schema dictionary."""

        if entry is None:
            entry = {}
        return {
            vol.Required(
                CONF_USERNAME,
                default=entry.get(CONF_USERNAME),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.EMAIL, autocomplete="username"
                )
            ),
            vol.Required(
                CONF_PASSWORD,
                default=entry.get(CONF_PASSWORD),
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                ),
            ),
            vol.Required(
                CONF_COUNTRY_CODE,
                default=entry.get(CONF_COUNTRY_CODE) or self.hass.config.country,
            ): selector.CountrySelector(
                selector.CountrySelectorConfig(),
            ),
            vol.Required(
                ACCEPT_TERMS,
                default=entry.get(ACCEPT_TERMS, _ACCEPT_TERMS),
            ): selector.BooleanSelector(),
        }


class AnkerSolixOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        if AwesomeVersion(HAVERSION) < "2024.11.99":
            self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle options flow."""
        errors: dict[str, str] = {}
        placeholders: dict[
            str, str
        ] = {}  # NOTE: Passed option placeholder do not work with translation files, HASS Bug?
        placeholders[MQTT_LINK] = MQ_LINK

        existing_options = self.config_entry.options.copy()

        if user_input:
            test_options = user_input.get(CONF_TEST_OPTIONS, {})
            if test_options.get(TESTFOLDER) or not test_options.get(TESTMODE):
                # merge new options from user form with existing options in config entry
                return self.async_create_entry(
                    title="",
                    data=existing_options | user_input,
                    description_placeholders=placeholders,
                )
            # Test mode enabled but no existing folder selected
            errors[TESTFOLDER] = "folder_invalid"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                await get_options_schema(user_input or self.config_entry.options)
            ),
            errors=errors,
            description_placeholders=placeholders,
        )


async def get_options_schema(entry: dict | None = None) -> dict:
    """Create the options schema dictionary."""

    if entry is None:
        entry = {}
    api_options = entry.get(CONF_API_OPTIONS, {})
    api_options_schema = {
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=api_options.get(
                CONF_SCAN_INTERVAL,
                SCAN_INTERVAL_DEF,
            ),
        ): vol.All(
            cv.positive_int,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_SCAN_INTERVAL_MIN,
                    max=_SCAN_INTERVAL_MAX,
                    step=_SCAN_INTERVAL_STEP,
                    unit_of_measurement="sec",
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
        ),
        vol.Optional(
            INTERVALMULT,
            default=api_options.get(INTERVALMULT, INTERVALMULT_DEF),
        ): vol.All(
            cv.positive_int,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_INTERVALMULT_MIN,
                    max=_INTERVALMULT_MAX,
                    step=_INTERVALMULT_STEP,
                    unit_of_measurement="updates",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        ),
        vol.Optional(
            CONF_DELAY_TIME,
            default=api_options.get(CONF_DELAY_TIME, DELAY_TIME_DEF),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=_DELAY_TIME_MIN,
                max=_DELAY_TIME_MAX,
                step=_DELAY_TIME_STEP,
                unit_of_measurement="sec",
                mode=selector.NumberSelectorMode.SLIDER,
            ),
        ),
        vol.Optional(
            CONF_TIMEOUT,
            default=api_options.get(CONF_TIMEOUT, TIMEOUT_DEF),
        ): vol.All(
            cv.positive_int,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_TIMEOUT_MIN,
                    max=_TIMEOUT_MAX,
                    step=_TIMEOUT_STEP,
                    unit_of_measurement="sec",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        ),
        vol.Optional(
            CONF_ENDPOINT_LIMIT,
            default=api_options.get(CONF_ENDPOINT_LIMIT, ENDPOINT_LIMIT_DEF),
        ): vol.All(
            cv.positive_int,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_ENDPOINT_LIMIT_MIN,
                    max=_ENDPOINT_LIMIT_MAX,
                    step=_ENDPOINT_LIMIT_STEP,
                    unit_of_measurement="requests",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        ),
        vol.Optional(
            CONF_SKIP_INVALID,
            default=api_options.get(CONF_SKIP_INVALID, SKIP_INVALID_DEF),
        ): selector.BooleanSelector(),
    }
    mqtt_options = entry.get(CONF_MQTT_OPTIONS, {})
    mqtt_options_schema = {
        vol.Optional(
            CONF_MQTT_USAGE,
            default=mqtt_options.get(CONF_MQTT_USAGE, MQTT_USAGE_DEF),
        ): selector.BooleanSelector(),
        vol.Optional(
            CONF_TRIGGER_TIMEOUT,
            default=mqtt_options.get(
                CONF_TRIGGER_TIMEOUT,
                TRIGGER_TIMEOUT_DEF,
            ),
        ): vol.All(
            cv.positive_int,
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_TRIGGER_TIMEOUT_MIN,
                    max=_TRIGGER_TIMEOUT_MAX,
                    step=_TRIGGER_TIMEOUT_STEP,
                    unit_of_measurement="sec",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        ),
    }

    schema = {
        # Items grouped for Api options
        vol.Required(CONF_API_OPTIONS): section(
            vol.Schema(api_options_schema),
            {"collapsed": True},
        ),
        # Items grouped for MQTT options
        vol.Required(CONF_MQTT_OPTIONS): section(
            vol.Schema(mqtt_options_schema),
            {"collapsed": True},
        ),
        vol.Optional(
            CONF_EXCLUDE,
            default=entry.get(
                CONF_EXCLUDE,
                list(api_client.DEFAULT_EXCLUDE_CATEGORIES),
            ),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(api_client.API_CATEGORIES),
                # mode="dropdown",
                # mode="list",
                sort=False,
                multiple=True,
                translation_key=CONF_EXCLUDE,
            )
        ),
    }
    if _ALLOW_TESTMODE:
        if not (jsonfolders := await api_client.json_example_folders()):
            # Add empty element to ensure proper list validation
            jsonfolders = [""]
        jsonfolders.sort()
        test_options = entry.get(CONF_TEST_OPTIONS, {})
        test_options_schema = {
            vol.Optional(
                TESTMODE,
                default=test_options.get(TESTMODE, False),
            ): selector.BooleanSelector(),
            vol.Optional(
                TESTFOLDER,
                description={
                    "suggested_value": test_options.get(
                        TESTFOLDER, next(iter(jsonfolders), "")
                    )
                },
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=jsonfolders, mode="dropdown")
            ),
            vol.Optional(
                CONF_MQTT_TEST_SPEED,
                default=test_options.get(CONF_MQTT_TEST_SPEED, _MQTT_POLLER_SPEED_DEF),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=_MQTT_POLLER_SPEED_MIN,
                    max=_MQTT_POLLER_SPEED_MAX,
                    step=_MQTT_POLLER_SPEED_MIN,
                    unit_of_measurement="",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        }
        schema.update(
            {
                # Items grouped for Test options
                vol.Required(CONF_TEST_OPTIONS): section(
                    vol.Schema(test_options_schema),
                    {"collapsed": False},
                ),
            }
        )
    return schema


async def async_check_and_remove_devices(
    hass: HomeAssistant,
    user_input: dict[str, Any],
    apidata: dict,
    excluded: set | None = None,
    configured_user: str | None = None,
) -> config_entries.ConfigEntry | None:
    """Check if given user input with its initial apidata has shared devices with existing configuration.

    If there are none, remove devices of this config that are no longer available for the configuration.
    """

    obsolete_user_devs = {}
    # ensure device type is also excluded when subcategories are excluded to remove device entities with reload from registry
    if excluded:
        # Subcategories for Account devices
        if {
            SolixDeviceType.VEHICLE.value,
            ApiCategories.account_info,
            ApiCategories.mqtt_devices,
        } & excluded:
            excluded = excluded | {SolixDeviceType.ACCOUNT.value}
        # Subcategories for System devices
        if {
            ApiCategories.site_price,
            SolixDeviceType.SOLARBANK.value,
            SolixDeviceType.SOLARBANK_PPS.value,
            SolixDeviceType.INVERTER.value,
            SolixDeviceType.PPS.value,
            SolixDeviceType.POWERPANEL.value,
            SolixDeviceType.SMARTMETER.value,
            SolixDeviceType.SMARTPLUG.value,
            SolixDeviceType.HES.value,
            SolixDeviceType.EV_CHARGER.value,
            SolixDeviceType.CHARGER.value,
            SolixDeviceType.COMBINER_BOX.value,
            ApiCategories.solarbank_energy,
            ApiCategories.smartmeter_energy,
            ApiCategories.smartplug_energy,
            ApiCategories.solar_energy,
            ApiCategories.powerpanel_energy,
            ApiCategories.hes_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.SYSTEM.value}
        # Subcategories for Solarbank only
        if {
            ApiCategories.solarbank_cutoff,
            ApiCategories.solarbank_fittings,
            ApiCategories.solarbank_solar_info,
            ApiCategories.solarbank_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.SOLARBANK.value}
        # Subcategories for Smart Plugs only
        if {
            ApiCategories.smartplug_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.SMARTPLUG.value}
        # Subcategories for Smart Meter only
        if {
            ApiCategories.smartmeter_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.SMARTMETER.value}
        # Subcategories for Power Panels only
        if {
            ApiCategories.powerpanel_avg_power,
            ApiCategories.powerpanel_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.POWERPANEL.value}
        # Subcategories for HES only
        if {
            ApiCategories.hes_avg_power,
            ApiCategories.hes_energy,
        } & excluded:
            excluded = excluded | {SolixDeviceType.HES.value}
        # Subcategories for all managed Devices
        if {
            ApiCategories.device_auto_upgrade,
            ApiCategories.device_tag,
            ApiCategories.mqtt_devices,
        } & excluded:
            excluded = excluded | {
                SolixDeviceType.SOLARBANK.value,
                SolixDeviceType.SOLARBANK_PPS.value,
                SolixDeviceType.INVERTER.value,
                SolixDeviceType.PPS.value,
                SolixDeviceType.POWERPANEL.value,
                SolixDeviceType.SMARTMETER.value,
                SolixDeviceType.SMARTPLUG.value,
                SolixDeviceType.HES.value,
                SolixDeviceType.EV_CHARGER.value,
                SolixDeviceType.CHARGER.value,
                SolixDeviceType.COMBINER_BOX.value,
                SolixDeviceType.POWERBANK.value,
                SolixDeviceType.POWERCOOLER.value,
            }

    # get all device entries for a domain
    cfg_entries = hass.config_entries.async_entries(domain=DOMAIN)
    for cfg_entry in cfg_entries:
        device_entries = dr.async_entries_for_config_entry(
            dr.async_get(hass), cfg_entry.entry_id
        )
        cfg_username = cfg_entry.data.get(CONF_USERNAME)
        for dev_entry in device_entries:
            if (
                username := str(user_input.get(CONF_USERNAME) or "")
            ) and username != cfg_username:
                # config entry of another account
                if (
                    dev_entry.serial_number in apidata
                    and configured_user != cfg_username
                ):
                    return cfg_entry
            # device is registered for same account, check if still used in coordinator data or excluded and add to obsolete list for removal
            elif dev_entry.serial_number not in apidata or (
                excluded
                and not {apidata.get(dev_entry.serial_number, {}).get("type")}
                - excluded
            ):
                obsolete_user_devs[dev_entry.id] = dev_entry.serial_number

    # Remove the obsolete device entries if not only checking for configured user during switch
    if not configured_user and obsolete_user_devs:
        dev_registry = None
        # Save actual restore states before removal
        await restore_state.RestoreStateData.async_save_persistent_states(hass)
        LOGGER.info("Saved HA states of restore entities prior removing devices")
        for dev_id, serial in obsolete_user_devs.items():
            # ensure to obtain dev registry again if no longer available
            if dev_registry is None:
                dev_registry = dr.async_get(hass)
            dev_registry.async_remove_device(dev_id)
            # NOTE: removal of any underlying entities is handled by core
            LOGGER.info(
                "Removed device entry %s from registry for device %s due to excluded entities or unused device",
                dev_id,
                serial,
            )
    return None
