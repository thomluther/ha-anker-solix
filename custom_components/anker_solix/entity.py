"""AnkerSolixEntity class."""

from __future__ import annotations  # noqa: I001

from dataclasses import dataclass
from enum import IntFlag

from .solixapi.apitypes import SolixSiteType
from .const import IMAGEFOLDER, DOMAIN, MANUFACTURER
from pathlib import Path
from homeassistant.helpers.entity import DeviceInfo


@dataclass(frozen=True)
class AnkerSolixPicturePath:
    """Definition of picture path for device types."""

    LOCALPATH: str = str(Path("/local"))
    IMAGEPATH: str = str(Path(LOCALPATH) / "community" / DOMAIN / IMAGEFOLDER)

    SOLARBANK: str = str(Path(IMAGEPATH) / "Solarbank_E1600_pub.png")
    INVERTER: str = str(Path(IMAGEPATH) / "MI80_A5143_pub.png")
    SMARTMETER: str = str(Path(IMAGEPATH) / "Smartmeter_A17X7_pub.png")
    SMARTPLUG: str = str(Path(IMAGEPATH) / "Smart_plug_A17X8.png")
    COMBINER_BOX: str = str(Path(IMAGEPATH) / "Power_Dock_AE100_pub.png")
    PPS: str = str(Path(IMAGEPATH) / "PPS_F1200_A1771_pub.png")
    POWERPANEL: str = str(Path(IMAGEPATH) / "Power_Panel_A17B1.png")
    HES: str = str(Path(IMAGEPATH) / "HES_X1_A5101.png")
    SOLARBANK_PPS: str = str(Path(IMAGEPATH) / "Solarbank_PPS_F3000_A1782.png")
    POWERCOOLER: str = str(Path(IMAGEPATH) / "Everfrost_2_40L_A17A4_pub.png")
    CHARGER: str = str(Path(IMAGEPATH) / "Charger_250W_A2345_pub.png")
    EV_CHARGER: str = str(Path(IMAGEPATH) / "EV_Charger_A5191_pub.png")
    VEHICLE: str = str(Path(IMAGEPATH) / "Electric_Vehicle.png")

    A17B1: str = str(Path(IMAGEPATH) / "Power_Panel_A17B1.png")

    A17C0: str = str(Path(IMAGEPATH) / "Solarbank_E1600_pub.png")
    A17C1: str = str(Path(IMAGEPATH) / "Solarbank_2_pro_A17C1_pub.png")
    A17C2: str = str(Path(IMAGEPATH) / "Solarbank_2_A17C2_pub.png")
    A17C3: str = str(Path(IMAGEPATH) / "Solarbank_2_plus_A17C3_pub.png")
    A17C5: str = str(Path(IMAGEPATH) / "Solarbank_3_pro_A17C5_pub.png")
    A17Y0: str = str(Path(IMAGEPATH) / "Fitting_A17Y0_pub.png")

    A5140: str = str(Path(IMAGEPATH) / "MI60_A5140_pub.png")
    A5143: str = str(Path(IMAGEPATH) / "MI80_A5143_pub.png")

    A17X7: str = str(Path(IMAGEPATH) / "Smartmeter_A17X7_pub.png")
    A17X7US: str = str(Path(IMAGEPATH) / "Smartmeter_A17X7US.png")
    AE1R0: str = str(Path(IMAGEPATH) / "Smartmeter_AE1R0_pub.png")
    SHEM3: str = str(Path(IMAGEPATH) / "Shelly_Pro_3EM.png")
    SHEMP3: str = str(Path(IMAGEPATH) / "Shelly_Pro_3EM.png")

    A17X8: str = str(Path(IMAGEPATH) / "Smart_plug_A17X8.png")
    SHPPS: str = str(Path(IMAGEPATH) / "Shelly_plus_plug_s_black.png")

    AE100: str = str(Path(IMAGEPATH) / "Power_Dock_AE100_pub.png")

    A1722: str = str(Path(IMAGEPATH) / "PPS_C300_A1722_pub.png")
    A1723: str = str(Path(IMAGEPATH) / "PPS_C200_A1723_A1725_pub.png")
    A1725: str = str(Path(IMAGEPATH) / "PPS_C200_A1723_A1725_pub.png")
    A1726: str = str(Path(IMAGEPATH) / "PPS_C300DC_A1726_pub.png")
    A1727: str = str(Path(IMAGEPATH) / "PPS_C200DC_A1727_pub.png")
    A1728: str = str(Path(IMAGEPATH) / "PPS_C300X_A1728_pub.png")
    A1753: str = str(Path(IMAGEPATH) / "PPS_C800X_A1755_pub.png")
    A1754: str = str(Path(IMAGEPATH) / "PPS_C800X_A1755_pub.png")
    A1755: str = str(Path(IMAGEPATH) / "PPS_C800X_A1755_pub.png")
    A1761: str = str(Path(IMAGEPATH) / "PPS_C1000X_A1761_pub.png")
    A1762: str = str(Path(IMAGEPATH) / "PPS_1000_A1762_pub.png")
    A1770: str = str(Path(IMAGEPATH) / "PPS_F1200_A1771_pub.png")
    A1771: str = str(Path(IMAGEPATH) / "PPS_F1200_A1771_pub.png")
    A1772: str = str(Path(IMAGEPATH) / "PPS_F1500_A1772_pub.png")
    A1780: str = str(Path(IMAGEPATH) / "PPS_F2000_A1780_pub.png")
    A1781: str = str(Path(IMAGEPATH) / "PPS_F2600_A1781_pub.png")
    A1782: str = str(Path(IMAGEPATH) / "Solarbank_PPS_F3000_A1782.png")
    A1790: str = str(Path(IMAGEPATH) / "PPS_F3800_A1790_pub.png")
    A1790P: str = str(Path(IMAGEPATH) / "PPS_F3800_A1790P_pub.png")
    A17B2: str = str(Path(IMAGEPATH) / "Fitting_A17B2_pub.png")
    A17D0: str = str(Path(IMAGEPATH) / "Fitting_A17D0_pub.png")
    A17D4: str = str(Path(IMAGEPATH) / "Fitting_A17D4_pub.png")

    A17A0: str = str(Path(IMAGEPATH) / "PowerCooler30_A17A0_pub.png")
    A17A1: str = str(Path(IMAGEPATH) / "PowerCooler40_A17A1_pub.png")
    A17A2: str = str(Path(IMAGEPATH) / "PowerCooler50_A17A2_pub.png")
    A17A3: str = str(Path(IMAGEPATH) / "Everfrost_2_23L_A17A3_pub.png")
    A17A4: str = str(Path(IMAGEPATH) / "Everfrost_2_40L_A17A4_pub.png")
    A17A5: str = str(Path(IMAGEPATH) / "Everfrost_2_58L_A17A5_pub.png")

    A5101: str = str(Path(IMAGEPATH) / "HES_X1_A5101.png")
    A5102: str = str(Path(IMAGEPATH) / "HES_X1_A5101.png")
    A5103: str = str(Path(IMAGEPATH) / "HES_X1_A5101.png")
    A5220: str = str(Path(IMAGEPATH) / "HES_A5220_pub.png")
    A5150: str = str(Path(IMAGEPATH) / "HES_A5150_pub.png")
    A5341: str = str(Path(IMAGEPATH) / "HES_A5341_pub.png")
    A5450: str = str(Path(IMAGEPATH) / "HES_A5450_pub.png")

    A5191: str = str(Path(IMAGEPATH) / "EV_Charger_A5191_pub.png")

    A2345: str = str(Path(IMAGEPATH) / "Charger_250W_A2345_pub.png")
    A91B2: str = str(Path(IMAGEPATH) / "Charger_240W_A91B2_pub.png")


@dataclass(frozen=True)
class AnkerSolixEntityType:
    """Definition of entity types used."""

    ACCOUNT: str = "account"
    SITE: str = "site"
    DEVICE: str = "device"
    VEHICLE: str = "vehicle"


@dataclass(frozen=True)
class AnkerSolixEntityRequiredKeyMixin:
    """Sensor entity description with required extra keys."""

    json_key: str


class AnkerSolixEntityFeature(IntFlag):
    """Supported features of the Anker Solix Entities."""

    SOLARBANK_SCHEDULE = 1
    ACCOUNT_INFO = 2
    SYSTEM_INFO = 4
    AC_CHARGE = 8


def get_AnkerSolixSubdeviceInfo(
    data: dict, identifier: str, maindevice: str
) -> DeviceInfo:
    """Return an Anker Solix Sub Device DeviceInfo."""

    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=MANUFACTURER,
        model=data.get("name") or data.get("device_pn"),
        # Use new model_id attribute supported since core 2024.8.0
        model_id=data.get("device_pn"),
        serial_number=data.get("device_sn"),
        name=data.get("alias") or data.get("name"),
        sw_version=data.get("sw_version"),
        # map to main device
        via_device=(DOMAIN, maindevice),
    )


def get_AnkerSolixDeviceInfo(data: dict, identifier: str, account: str) -> DeviceInfo:
    """Return an Anker Solix End Device DeviceInfo."""

    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=MANUFACTURER,
        model=data.get("name") or data.get("device_pn"),
        # Use new model_id attribute supported since core 2024.8.0
        model_id=data.get("device_pn"),
        serial_number=data.get("device_sn"),
        name=data.get("alias") or data.get("name"),
        sw_version=data.get("sw_version"),
        # map to site, or map standalone devices to account device
        via_device=(DOMAIN, data.get("site_id") or account),
    )


def get_AnkerSolixSystemInfo(data: dict, identifier: str, account: str) -> DeviceInfo:
    """Return an Anker Solix System DeviceInfo."""

    power_site_type = data.get("power_site_type")
    site_type = getattr(SolixSiteType, "t_" + str(power_site_type), "")
    if account:
        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            manufacturer=MANUFACTURER,
            serial_number=data.get("site_id"),
            model=(str(site_type).capitalize() + " Site").strip(),
            model_id=f"Type {data.get('power_site_type')}",
            name=f"System {data.get('site_name')}",
            via_device=(DOMAIN, account),
        )
    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=MANUFACTURER,
        serial_number=data.get("site_id"),
        model=(str(site_type).capitalize() + " Site").strip(),
        model_id=f"Type {data.get('power_site_type')}",
        name=f"System {data.get('site_name')}",
    )


def get_AnkerSolixAccountInfo(
    data: dict,
    identifier: str,
) -> DeviceInfo:
    """Return an Anker Solix Account DeviceInfo."""

    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=MANUFACTURER,
        serial_number=identifier,
        model=str(data.get("type")).capitalize(),
        model_id=data.get("server"),
        name=f"{data.get('nickname')} ({str(data.get('country') or '--').upper()})",
    )


def get_AnkerSolixVehicleInfo(data: dict, identifier: str, account: str) -> DeviceInfo:
    """Return an Anker Solix Vehicle DeviceInfo."""

    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        manufacturer=data.get("brand"),
        serial_number=identifier,
        model=str(data.get("type")).capitalize(),
        model_id=data.get("model"),
        hw_version=data.get("productive_year"),
        name=data.get("vehicle_name"),
        via_device=(DOMAIN, account),
    )
