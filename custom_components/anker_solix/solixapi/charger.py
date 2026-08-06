"""Anker Power/Solix Cloud API class charger (aka mini_power) related methods."""
# ruff: noqa: N806

from __future__ import annotations  # noqa: TID251

from pathlib import Path
from typing import TYPE_CHECKING

from .apitypes import API_ENDPOINTS, API_FILEPREFIXES

if TYPE_CHECKING:
    from .api import AnkerSolixApi


async def get_charger_custom_mode_list(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger custom charging mode list as defined by user.

    Example data:
    "charging_mode_list": [
        {"id":24581,"number":1,"name":"test","total_power":30,"max_total_power":250,"auto_exit":0,"has_charge_protocol":1,"power_settings":[
            {"name":"C1","power":0,"max_power":140,"input_power":0,"input_max_power":0,"scp":0,"ufcs":0,"pps11v":0,"pps16v":0,"pps20v":0,"pd12v":0,"huawei":0,"xiaomi":0},
            {"name":"C2","power":0,"max_power":100,"input_power":0,"input_max_power":0,"scp":0,"ufcs":0,"pps11v":0,"pps16v":0,"pps20v":0,"pd12v":0,"huawei":0,"xiaomi":0},
            {"name":"C3","power":0,"max_power":100,"input_power":0,"input_max_power":0,"scp":0,"ufcs":0,"pps11v":0,"pps16v":0,"pps20v":0,"pd12v":0,"huawei":0,"xiaomi":0},
            {"name":"C4","power":15,"max_power":100,"input_power":0,"input_max_power":0,"scp":0,"ufcs":1,"pps11v":0,"pps16v":0,"pps20v":0,"pd12v":0,"huawei":0,"xiaomi":0},
            {"name": "A","power": 15,"max_power": 24,"input_power": 0,"input_max_power": 0,"scp": 0,"ufcs": 0,"pps11v": 0,"pps16v": 0,"pps20v": 0,"pd12v": 0,"huawei": 0,"xiaomi": 0}]}
    """
    data = {"device_sn": deviceSn}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_charging_modes']}_modified_{deviceSn}.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_charging_modes']}_{deviceSn}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_charging_modes"], json=data
        )
    data = resp.get("data") or {}
    # update device details
    ids = {}
    # Map custom mode IDs to dictionary for fast lookup
    for mode in data.get("charging_mode_list") or []:
        if (mode_id := mode.get("id")) is not None:
            ids[str(mode_id)] = mode
    if ids:
        self._update_dev({"device_sn": deviceSn, "custom_modes": ids})
    return data


def get_charger_custom_mode_profile(
    self: AnkerSolixApi,
    deviceSn: str,
    profile_number: str | int | None = None,
    profile_name: str | None = None,
) -> dict:
    """Get the mini charger custom charging mode profile by number or name from existing profiles."""
    if isinstance(deviceSn, str):
        if not isinstance(profile_number, str | int) or profile_number == "":
            profile_number = None
        if not isinstance(profile_name, str) or profile_name == "":
            profile_name = None
        return next(
            (
                profile
                for profile in self.devices.get(deviceSn, {})
                .get("custom_modes", {})
                .values()
                if profile.get("name", "") == profile_name
                or str(profile.get("number", "")) == str(profile_number)
            ),
            {},
        )
    return {}


def get_charger_custom_mode_options(
    self: AnkerSolixApi,
    deviceSn: str,
    by_number: bool = False,
) -> list:
    """Get the mini charger custom charging mode options by name or optionally by number from existing profiles."""
    # check if custom mode feature is enabled
    if isinstance(deviceSn, str) and (dev := self.devices.get(deviceSn, {})).get(
        "device_setting", {}
    ).get("charging_mode_status"):
        return [
            str(profile.get("number" if by_number else "name", ""))
            for profile in dev.get("custom_modes", {}).values()
        ]
    return []


async def get_charger_device_setting(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger device settings.

    Example data:
    {"device_setting": {"charging_mode_status": 0,"compatibility_status": 0,"antiloss_mode_status": 0,"temperature_mode_status": 0,"charging_device_identity_status": 0}}
    """
    data = {"device_sn": deviceSn}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_device_setting']}_modified_{deviceSn}.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_device_setting']}_{deviceSn}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_device_setting"], json=data
        )
    data = resp.get("data") or {}
    # update device details
    if data:
        self._update_dev({"device_sn": deviceSn} | data)
    return data


async def get_charger_port_remarks(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger port remarks.

    Example data:
    {"port_remarks": [
        {"port_name": "C1","remark": "MacBook"},
        {"port_name": "C2","remark": "Laptop"},
        {"port_name": "C3","remark": ""},
        {"port_name": "C4","remark": "SmartPhone"}]}
    """
    data = {"device_sn": deviceSn}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_port_remarks']}_modified_{deviceSn}.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_port_remarks']}_{deviceSn}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_port_remarks"], json=data
        )
    data = resp.get("data") or {}
    # update device details
    if data:
        self._update_dev({"device_sn": deviceSn} | data)
    return data


async def set_charger_port_remark(
    self,
    deviceSn: str,
    portName: str,
    remark: str = "",  # C1, C2, C3, C4, A1, A2
    toFile: bool = False,
) -> bool | dict:
    """Set the charker port remark (label) for the device.

    Example input:
    {"device_sn": deviceSn, "port_name": "C3", "remark": "iPhone"}
    """
    if (
        not isinstance(remark, str)
        or not isinstance(portName, str)
        or portName.upper() not in ["C1", "C2", "C3", "C4", "A1", "A2"]
    ):
        return False
    # Prepare payload
    portName = portName.upper()
    data = {"device_sn": deviceSn, "port_name": portName, "remark": remark}
    if toFile:
        # For file data, obtain existing data to be updated for test purpose
        filedata = await self.get_charger_port_remarks(
            deviceSn=deviceSn, fromFile=toFile
        )
        # update active setting in filedata
        remarks = []
        for port in filedata.get("port_remarks") or []:
            if (name := port.get("port_name", "")) >= portName and remark is not None:
                # insert/replace port in new list
                remarks.append({"port_name": portName, "remark": remark})
                remark = None
            if name != portName:
                # add port to new list
                remarks.append(port)
        filedata["port_remarks"] = remarks
        # Write data file for testing purposes
        if filedata and not await self.apisession.saveToFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['charger_get_port_remarks']}_modified_{deviceSn}.json",
            data={
                "code": 0,
                "msg": "success!",
                "data": filedata,
            },
        ):
            return False
    else:
        # Make the Api call and check for return code
        code = (
            await self.apisession.request(
                "post", API_ENDPOINTS["charger_set_port_remark"], json=data
            )
        ).get("code")
        if not isinstance(code, int) or int(code) != 0:
            return False
    # update the data in api dict and return active data
    return await self.get_charger_port_remarks(deviceSn=deviceSn, fromFile=toFile)


async def get_charger_screensavers(
    self: AnkerSolixApi,
    devicePn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger stock screensavers for given model.

    Example Api data:
    {"category": [
        {"id": "Futuristic","category_name": "Futuristic","list": [
            {"id": "948897111","title": "Celestial",
            "image_url": "https://public-aiot-ore-qa.s3.dualstack.us-west-2.amazonaws.com/anker-power/public/banner/2025/03/26/iot-admin/T5IyObNNgxhUVPH8/%E6%B0%94%E6%B3%A1.jpg",
            "file_crc32": "0x40914327","text_color": "","bin_url": ""},
            {"id": "236632206","title": "Robotic",
            "image_url": "https://public-aiot-ore-qa.s3.dualstack.us-west-2.amazonaws.com/anker-power/public/banner/2025/03/26/iot-admin/ZOXFASuOK3154M0O/%E6%9C%BA%E7%94%B2.jpg",
            "file_crc32": "0x756eab66","text_color": "","bin_url": ""}]},
        {"id": "Cosmic","category_name": "Cosmic","list": [
            {"id": "938963984","title": "Lunar",
            "image_url": "https://public-aiot-ore-qa.s3.dualstack.us-west-2.amazonaws.com/anker-power/public/banner/2025/03/26/iot-admin/dTHYjLQQJXwkoXJC/%E6%9C%88%E7%90%83.jpg",
            "file_crc32": "0xbd2ddca7","text_color": "","bin_url": ""},
            {"id": "819158638","title": "Galactic",
            "image_url": "https://public-aiot-ore-qa.s3.dualstack.us-west-2.amazonaws.com/anker-power/public/banner/2025/03/26/iot-admin/z0pv3dszhjkAYSfc/%E6%98%9F%E4%BA%91.jpg",
            "file_crc32": "0xdab95e74","text_color": "","bin_url": ""},
            {"id": "95294588","title": "Meteorite",""
            "image_url": "https://public-aiot-ore-qa.s3.dualstack.us-west-2.amazonaws.com/anker-power/public/banner/2025/03/26/iot-admin/xNe6kVzxj3C1aRKh/%E6%B5%81%E6%98%9F%E9%9B%A8.jpg",
            "file_crc32": "0x2c1f806","text_color": "","bin_url": ""}]}]}
    """

    data = {"product_code": devicePn}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['charger_get_screensavers']}_{devicePn}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_screensavers"], json=data
        )
    return resp.get("data") or {}


async def get_charger_manual_screensavers(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger manual screensavers defined by users for device.

    Example Api data:
    {"list": [
        {"id": 38820,"img_url": "https://edge-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker_power/edge/screen_saver/2026/07/12/472497a8f3bc0e58f449f3fa98972f07b5e2df4c/NA7sOGF4wHqzrE90.cropped_image.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4XHFIO3C7RXFIYK6%2F20260712%2Feu-central-1%2Fs3%2Faws4_request&X-Amz-Date=20260712T213013Z&X-Amz-Expires=300&X-Amz-SignedHeaders=host&X-Amz-Signature=3bc068f2a952db749c30b1f9abaf849400003e628a19aa9e5881f71fcc89ffbe",
        "short_url": "/anker_power/edge/screen_saver/2026/07/12/472497a8f3bc0e58f449f3fa98972f07b5e2df4c/NA7sOGF4wHqzrE90.cropped_image.jpg","hash_code": "0x14edd612",
        "name": "Feuerwerk","seq": 1}],
    "total": 1}
    """

    data = {"sn": deviceSn}
    if fromFile:
        resp = await self.apisession.loadFromFile(
            Path(self.testDir())
            / f"{API_FILEPREFIXES['charger_get_manual_screensavers']}_{deviceSn}.json"
        )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_manual_screensavers"], json=data
        )
    data = resp.get("data") or {}
    # update device details
    ids = {}
    # Flatten date to id dictionary for fast lookup and merge capability with flattened stock screensavers
    for theme in data.get("list") or []:
        if (theme_id := theme.get("id")) is not None:
            ids[str(theme_id)] = {
                "category_name": "Custom",
                "title": theme.get("name"),
                "file_hash": theme.get("hash_code"),
                "image_url": theme.get("img_url"),
                "id": theme_id,
                "theme_name": f"Custom - {theme.get('name')}",
            }
    if ids:
        self._update_dev({"device_sn": deviceSn, "screensaver": ids})
    return data


def get_charger_themes(
    self: AnkerSolixApi,
    deviceSn: str,
) -> dict:
    """Get the mini charger merged themes with stock and custom screensavers."""

    if isinstance(deviceSn, str):
        dev = self.devices.get(deviceSn) or {}
        return self.account.get("screensaver", {}).get(
            dev.get("device_pn", ""), {}
        ).get("themes", {}) | dev.get("screensaver", {})
    return {}


def get_charger_theme_options(
    self: AnkerSolixApi, deviceSn: str, theme_id: str | int | None = None
) -> list:
    """Get the mini charger screensaver theme options with category name and theme title."""
    if isinstance(deviceSn, str):
        if not isinstance(theme_id, str | int):
            theme_id = None
        else:
            theme_id = str(theme_id)
        # prepare lookup mapping
        if (
            theme_id
            and str(
                (theme := self.devices.get(deviceSn, {}).get("display_theme", {})).get(
                    "id"
                )
                or None
            )
            == theme_id
        ):
            themes = {theme_id: theme}
        else:
            themes = self.get_charger_themes(deviceSn)
            if theme_id:
                themes = {theme_id: themes.get(theme_id)} if theme_id in themes else {}
        return [theme.get("theme_name") for theme in themes.values()]
    return []


async def get_charger_protocol_status(
    self: AnkerSolixApi,
    deviceSn: str,
    fromFile: bool = False,
) -> dict:
    """Get the charger protocol status for the device.

    Example data:
    {"protocol_status": false,"modes": [
        {"mode": "ai","protocols": [
            {"protocol_key": "UFCS","status": true},
            {"protocol_key": "SCP","status": true},
            {"protocol_key": "5-16V PPS","status": true},
            {"protocol_key": "5-11V PPS","status": true}]},
        {"mode": "normal","protocols": [
            {"protocol_key": "UFCS","status": true},
            {"protocol_key": "SCP","status": true},
            {"protocol_key": "5-16V PPS","status": true},
            {"protocol_key": "5-11V PPS","status": true},
            {"protocol_key": "4.5-21V PPS","status": true}]}]}
    """
    data = {"device_sn": deviceSn}
    if fromFile:
        # For file data, verify first if there is a modified file to be used for testing
        if not (
            resp := await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_protocol_status']}_modified_{deviceSn}.json"
            )
        ):
            resp = await self.apisession.loadFromFile(
                Path(self.testDir())
                / f"{API_FILEPREFIXES['charger_get_protocol_status']}_{deviceSn}.json"
            )
    else:
        resp = await self.apisession.request(
            "post", API_ENDPOINTS["charger_get_protocol_status"], json=data
        )
    data = resp.get("data") or {}
    # update device details
    if data:
        self._update_dev({"device_sn": deviceSn} | data)
    return data
