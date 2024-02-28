"""AnkerSolixEntity class."""
from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from .const import IMAGEFOLDER, DOMAIN, MANUFACTURER
import os
from homeassistant.helpers.entity import DeviceInfo


@dataclass(frozen=True)
class AnkerSolixPicturePath:
    """Definition of picture path for device types."""

    IMAGEPATH: str = os.path.join(os.sep, "local", DOMAIN, IMAGEFOLDER)

    SOLARBANK: str = os.path.join(IMAGEPATH, "Solarbank_E1600_pub.png")
    INVERTER: str = os.path.join(IMAGEPATH, "MI80_A5143_pub.png")
    PPS: str = os.path.join(IMAGEPATH, "PPS_F1200_A1771_pub.png")
    POWERPANEL: str = os.path.join(IMAGEPATH, "Power_Panel_A17B1.png")
    ZEROWSWITCH: str = os.path.join(IMAGEPATH, "Fitting_A17Y0_pub.png")


@dataclass(frozen=True)
class AnkerSolixEntityType:
    """Definition of entity types used."""

    SITE: str = "site"
    DEVICE: str = "device"


@dataclass(frozen=True)
class AnkerSolixEntityRequiredKeyMixin:
    """Sensor entity description with required extra keys."""

    json_key: str


def get_AnkerSolixDeviceInfo(
    data: dict,
    identifier: str,
) -> DeviceInfo:
    """Return an Anker Solix End Device DeviceInfo."""

    if pn := data.get("device_pn"):
        pn = f"({pn})"
    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=MANUFACTURER,
        model=" ".join([data.get("name") or "", pn]),
        serial_number=data.get("device_sn"),
        name=data.get("alias"),
        sw_version=data.get("sw_version"),
        via_device=(DOMAIN, data.get("site_id")),
    )


def get_AnkerSolixSystemInfo(
    data: dict,
    identifier: str,
) -> DeviceInfo:
        """Return an Anker Solix System DeviceInfo."""

        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=MANUFACTURER,
            serial_number=data.get("site_id"),
            model=f'Power Site Type {data.get("power_site_type")}',
            name=f'System {data.get("site_name")}',
        )
