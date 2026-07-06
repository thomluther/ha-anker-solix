"""Diagnostics support for anker_solix."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .coordinator import AnkerSolixDataUpdateCoordinator

TO_REDACT = {"ip_address", "unique_id", "username", "password", "email", "owner_user_id", "bt_ble_mac", "wifi_mac", "wifi_name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if isinstance(coordinator, AnkerSolixDataUpdateCoordinator) and coordinator.client:
        # Wait until client cache is valid
        await coordinator.client.validate_cache()
        cache = coordinator.data or {}
        # redact keys from cache
        entry_dict = entry.as_dict()
        cache["account"] = cache.pop(entry_dict.get("unique_id"),{})
        return {
            "config_entry": async_redact_data(entry_dict, TO_REDACT),
            "cached_data": async_redact_data(cache, TO_REDACT),
        }
    return {}


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    coordinator: AnkerSolixDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if isinstance(coordinator, AnkerSolixDataUpdateCoordinator) and coordinator.client:
        # Wait until client cache is valid
        await coordinator.client.validate_cache()
        return {
            "cached_data": async_redact_data(
                coordinator.data.get(device.serial_number) or {}, TO_REDACT
            ),
        }
    return {}
