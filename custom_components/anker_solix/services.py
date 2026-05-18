"""Services for Anker Solix devices."""

from homeassistant.components import button, select, sensor, switch
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers import service

from .const import (
    DOMAIN,
    REQUEST_LINK,
    SERVICE_API_REQUEST,
    SERVICE_CLEAR_SOLARBANK_SCHEDULE,
    SERVICE_EXPORT_SYSTEMS,
    SERVICE_GET_DEVICE_INFO,
    SERVICE_GET_SOLARBANK_SCHEDULE,
    SERVICE_GET_SYSTEM_INFO,
    SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
    SERVICE_MODIFY_SOLIX_USE_TIME,
    SERVICE_SET_SOLARBANK_SCHEDULE,
    SERVICE_UPDATE_SOLARBANK_SCHEDULE,
    SOLARBANK_TIMESLOT_SCHEMA,
    SOLIX_BACKUP_CHARGE_SCHEMA,
    SOLIX_ENTITY_SCHEMA,
    SOLIX_EXPORT_SCHEMA,
    SOLIX_REQUEST_SCHEMA,
    SOLIX_USE_TIME_SCHEMA,
    SOLIX_WEEKDAY_SCHEMA,
)
from .entity import AnkerSolixEntityFeature


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Anker Solix services."""

    # Button entity actions
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_GET_DEVICE_INFO,
        entity_domain=button.DOMAIN,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_GET_DEVICE_INFO,
        required_features=[AnkerSolixEntityFeature.SYSTEM_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    # Select entity actions
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_MODIFY_SOLIX_USE_TIME,
        entity_domain=select.DOMAIN,
        schema=SOLIX_USE_TIME_SCHEMA,
        func=SERVICE_MODIFY_SOLIX_USE_TIME,
        required_features=[AnkerSolixEntityFeature.AC_CHARGE],
    )
    # Switch entity actions
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_EXPORT_SYSTEMS,
        entity_domain=switch.DOMAIN,
        schema=SOLIX_EXPORT_SCHEMA,
        func=SERVICE_EXPORT_SYSTEMS,
        required_features=[AnkerSolixEntityFeature.ACCOUNT_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_API_REQUEST,
        entity_domain=switch.DOMAIN,
        schema=SOLIX_REQUEST_SCHEMA,
        func=SERVICE_API_REQUEST,
        description_placeholders={
            "url": REQUEST_LINK,
        },
        required_features=[AnkerSolixEntityFeature.ACCOUNT_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        entity_domain=switch.DOMAIN,
        schema=SOLIX_BACKUP_CHARGE_SCHEMA,
        func=SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        required_features=[AnkerSolixEntityFeature.AC_CHARGE],
    )
    # Sensor entity actions
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_GET_SYSTEM_INFO,
        entity_domain=sensor.DOMAIN,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_GET_SYSTEM_INFO,
        required_features=[AnkerSolixEntityFeature.SYSTEM_INFO],
        supports_response=SupportsResponse.ONLY,
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_GET_SOLARBANK_SCHEDULE,
        entity_domain=sensor.DOMAIN,
        schema=SOLIX_ENTITY_SCHEMA,
        func=SERVICE_GET_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
        supports_response=SupportsResponse.ONLY,
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_CLEAR_SOLARBANK_SCHEDULE,
        entity_domain=sensor.DOMAIN,
        schema=SOLIX_WEEKDAY_SCHEMA,
        func=SERVICE_CLEAR_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_SET_SOLARBANK_SCHEDULE,
        entity_domain=sensor.DOMAIN,
        schema=SOLARBANK_TIMESLOT_SCHEMA,
        func=SERVICE_SET_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )
    service.async_register_platform_entity_service(
        hass=hass,
        service_domain=DOMAIN,
        service_name=SERVICE_UPDATE_SOLARBANK_SCHEDULE,
        entity_domain=sensor.DOMAIN,
        schema=SOLARBANK_TIMESLOT_SCHEMA,
        func=SERVICE_UPDATE_SOLARBANK_SCHEDULE,
        required_features=[AnkerSolixEntityFeature.SOLARBANK_SCHEDULE],
    )


@callback
def async_remove_services(hass: HomeAssistant) -> None:
    """Remove the Anker Solix services."""
    for action in [
        SERVICE_API_REQUEST,
        SERVICE_CLEAR_SOLARBANK_SCHEDULE,
        SERVICE_EXPORT_SYSTEMS,
        SERVICE_GET_DEVICE_INFO,
        SERVICE_GET_SOLARBANK_SCHEDULE,
        SERVICE_GET_SYSTEM_INFO,
        SERVICE_MODIFY_SOLIX_BACKUP_CHARGE,
        SERVICE_MODIFY_SOLIX_USE_TIME,
        SERVICE_SET_SOLARBANK_SCHEDULE,
        SERVICE_UPDATE_SOLARBANK_SCHEDULE,
    ]:
        hass.services.async_remove(DOMAIN, action)
