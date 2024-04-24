"""AnkerSolixEntity class."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from enum import IntFlag
from .const import IMAGEFOLDER, DOMAIN, MANUFACTURER
import os
from homeassistant.helpers.entity import DeviceInfo


@dataclass(frozen=True)
class AnkerSolixPicturePath:
    """Definition of picture path for device types."""

    LOCALPATH: str = os.path.join(os.sep, "local")
    IMAGEPATH: str = os.path.join(LOCALPATH, "community", DOMAIN, IMAGEFOLDER)

    SOLARBANK: str = os.path.join(IMAGEPATH, "Solarbank_E1600_pub.png")
    INVERTER: str = os.path.join(IMAGEPATH, "MI80_A5143_pub.png")
    PPS: str = os.path.join(IMAGEPATH, "PPS_F1200_A1771_pub.png")
    POWERPANEL: str = os.path.join(IMAGEPATH, "Power_Panel_A17B1.png")

    A17B1: str = os.path.join(IMAGEPATH, "Power_Panel_A17B1.png")

    A17C0: str = os.path.join(IMAGEPATH, "Solarbank_E1600_pub.png")
    A17Y0: str = os.path.join(IMAGEPATH, "Fitting_A17Y0_pub.png")

    A5140: str = os.path.join(IMAGEPATH, "MI60_A5140_pub.png")
    A5143: str = os.path.join(IMAGEPATH, "MI80_A5143_pub.png")

    A1753: str = os.path.join(IMAGEPATH, "PPS_C800X_A1755_pub.png")
    A1754: str = os.path.join(IMAGEPATH, "PPS_C800X_A1755_pub.png")
    A1755: str = os.path.join(IMAGEPATH, "PPS_C800X_A1755_pub.png")
    A1761: str = os.path.join(IMAGEPATH, "PPS_C1000X_A1761_pub.png")
    A1770: str = os.path.join(IMAGEPATH, "PPS_F1200_A1771_pub.png")
    A1771: str = os.path.join(IMAGEPATH, "PPS_F1200_A1771_pub.png")
    A1772: str = os.path.join(IMAGEPATH, "PPS_F1500_A1772_pub.png")
    A1780: str = os.path.join(IMAGEPATH, "PPS_F2000_A1780_pub.png")
    A1781: str = os.path.join(IMAGEPATH, "PPS_F2600_A1781_pub.png")
    A1790: str = os.path.join(IMAGEPATH, "PPS_F3800_A1790_pub.png")

    A17A0: str = os.path.join(IMAGEPATH, "PowerCooler30_A17A0_pub.png")
    A17A1: str = os.path.join(IMAGEPATH, "PowerCooler40_A17A1_pub.png")
    A17A2: str = os.path.join(IMAGEPATH, "PowerCooler50_A17A2_pub.png")


@dataclass(frozen=True)
class AnkerSolixEntityType:
    """Definition of entity types used."""

    SITE: str = "site"
    DEVICE: str = "device"


@dataclass(frozen=True)
class AnkerSolixEntityRequiredKeyMixin:
    """Sensor entity description with required extra keys."""

    json_key: str


class AnkerSolixEntityFeature(IntFlag):
    """Supported features of the Anker Solix Entities."""

    SOLARBANK_SCHEDULE = 1


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
