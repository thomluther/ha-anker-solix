"""Data poller modules to create/update Api cache structure for the Anker Power/Solix Cloud API."""

# flake8: noqa: SLF001

from asyncio import sleep
import contextlib
from datetime import datetime, timedelta

from .apibase import AnkerSolixBaseApi
from .apitypes import (
    ApiCategories,
    SolarbankStatus,
    SolixDeviceType,
    SolixParmType,
    SolixSiteType,
)
from .powerpanel import AnkerSolixPowerpanelApi


async def poll_sites(  # noqa: C901
    api: AnkerSolixBaseApi,
    siteId: str | None = None,
    fromFile: bool = False,
    exclude: set | None = None,
) -> dict:
    """Get the latest info for all accessible sites or only the provided siteId and update class sites and devices dictionaries used as cache.

    Example data:
    {'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c':
        {'site_info': {'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c', 'site_name': 'BKW', 'site_img': '', 'device_type_list': [3], 'ms_type': 1, 'power_site_type': 2, 'is_allow_delete': True},
        'site_admin': True,
        'home_info': {'home_name': 'Home', 'home_img': '', 'charging_power': '0.00', 'power_unit': 'W'},
        'solar_list': [],
        'pps_info': {'pps_list': [], 'total_charging_power': '0.00', 'power_unit': 'W', 'total_battery_power': '0.00', 'updated_time': '', 'pps_status': 0},
        'statistics': [{'type': '1', 'total': '89.75', 'unit': 'kwh'}, {'type': '2', 'total': '89.48', 'unit': 'kg'}, {'type': '3', 'total': '35.90', 'unit': '€'}],
        'topology_type': '1',
        'solarbank_info': {'solarbank_list': [{'device_pn': 'A17C0', 'device_sn': '9JVB42LJK8J0P5RY', 'device_name': 'Solarbank E1600',
            'device_img': 'https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png',
            'battery_power': '75', 'bind_site_status': '', 'charging_power': '0', 'power_unit': 'W', 'charging_status': '2', 'status': '0', 'wireless_type': '1', 'main_version': '', 'photovoltaic_power': '0',
            'output_power': '0', 'create_time': 1695392386, 'set_load_power': ''}],
            'total_charging_power': '0', 'power_unit': 'W', 'charging_status': '0', 'total_battery_power': '0.00', 'updated_time': '2023-12-28 18:53:27', 'total_photovoltaic_power': '0', 'total_output_power': '0.00',
            'display_set_power': False},
        'retain_load': '0W',
        'updated_time': '01-01-0001 00:00:00',
        'power_site_type': 2,
        'site_id': 'efaca6b5-f4a0-e82e-3b2e-6b9cf90ded8c',
        'powerpanel_list': []}}
    """
    # define excluded categories to skip for queries
    if not exclude or not isinstance(exclude, set):
        exclude = set()
    if siteId and (api.sites.get(siteId) or {}):
        # update only the provided site ID
        api._logger.debug("Updating Sites data for site ID %s", siteId)
        new_sites = api.sites
        # prepare the site list dictionary for the update loop by copying the requested site from the cache
        sites: dict = {"site_list": [api.sites[siteId].get("site_info") or {}]}
    else:
        # run normal refresh for all sites
        api._logger.debug("Updating Sites data")
        new_sites = {}
        api._logger.debug("Getting site list")
        sites = await api.get_site_list(fromFile=fromFile)
        api._site_devices = set()

    for site in sites.get("site_list", []):
        if myid := site.get("site_id"):
            # Update site info
            mysite: dict = api.sites.get(myid, {})
            siteInfo: dict = mysite.get("site_info", {})
            siteInfo.update(site)
            mysite.update({"type": SolixDeviceType.SYSTEM.value, "site_info": siteInfo})
            if hasattr(
                SolixSiteType, item := "t_" + str(siteInfo.get("power_site_type") or "")
            ):
                mysite["site_type"] = getattr(SolixSiteType, item)
            admin = (
                siteInfo.get("ms_type", 0) in [0, 1]
            )  # add boolean key to indicate whether user is site admin (ms_type 1 or not known) and can query device details
            mysite["site_admin"] = admin
            # Get product list once for device names if no admin and save it in account cache
            if not admin and "products" not in api.account:
                api._update_account(
                    {"products": await api.get_products(fromFile=fromFile)}
                )
            # Update scene info for site
            api._logger.debug("Getting scene info for site")
            scene = await api.get_scene_info(myid, fromFile=fromFile)
            # Check if Solarbank 2 data is valid, default to true if field not found or no Solarbank in system
            sb_info = scene.get("solarbank_info") or {}
            data_valid = (
                bool(sb_info.get("is_display_data", True))
                or len(sb_info.get("solarbank_list") or []) == 0
            )
            # Work around: Try few requeries if SB data is invalid in scene info response
            requeries = 0
            # Disabled requeries since they don't help, increase loop check counter if requeries should be done
            while requeries < 0 and not data_valid:
                requeries += 1
                api._logger.debug(
                    "Received invalid solarbank data, %s retry to get valid scene info for site",
                    requeries,
                )
                # delay 5 sec prior requery
                if not fromFile:
                    await sleep(5)
                scene = await api.get_scene_info(myid, fromFile=fromFile)
                sb_info = scene.get("solarbank_info") or {}
                data_valid = (
                    bool(sb_info.get("is_display_data", True))
                    or len(sb_info.get("solarbank_list") or []) == 0
                )
            # add indicator for valid data introduced for Solarbank 2 to site cache
            mysite.update({"data_valid": data_valid, "requeries": requeries})
            # copy old SB info data timestamp if new is invalid, because can be invalid even if data is valid
            # example       "updated_time": "1970-01-01 00:00:00",
            if sb_info.get("solarbank_list"):
                oldstamp = (mysite.get("solarbank_info") or {}).get(
                    "updated_time"
                ) or ""
                timestamp = datetime.now().replace(year=1970)
                fmt = "%Y-%m-%d %H:%M:%S"
                with contextlib.suppress(ValueError):
                    timestamp = datetime.strptime(sb_info.get("updated_time"), fmt)
                if timestamp.year == 1970:
                    # replace the field in the new scene referenced sb info
                    sb_info["updated_time"] = (
                        datetime.now().strftime(fmt)
                        if data_valid or not oldstamp
                        else oldstamp
                    )
            # check if power panel site type to maintain statistic object which will be updated and replaced only during site details refresh
            if mysite.get("site_type") == SolixDeviceType.POWERPANEL.value:
                # initialize the powerpanel Api if not done yet
                if not api.powerpanelApi:
                    api.powerpanelApi = AnkerSolixPowerpanelApi(
                        apisession=api.apisession
                    )
                # keep previous statistics since it should not overwrite stats updated by power panel site details update
                if "statistics" in mysite:
                    scene["statistics"] = mysite.get("statistics")
                # pass the site ID and site info to avoid another site list query
                await api.powerpanelApi.update_sites(
                    siteId=myid,
                    siteData=mysite | scene,
                    fromFile=fromFile,
                    exclude=exclude,
                )
                scene.update(api.powerpanelApi.sites.get(myid) or {})
            mysite.update(scene)
            new_sites.update({myid: mysite})
            # Update device details from scene info
            sb_total_charge = sb_info.get("total_charging_power", "")
            sb_total_output = sb_info.get("total_output_power", "")
            sb_total_solar = sb_info.get("total_photovoltaic_power", "")
            sb_total_charge_calc = 0
            sb_charges: dict = {}
            sb_list = sb_info.get("solarbank_list") or []
            for index, solarbank in enumerate(sb_list):
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in solarbank:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    solarbank = dict(solarbank).copy()
                    solarbank.update({"alias_name": solarbank.pop("device_name")})
                # work around for system and device output presets in dual solarbank setups, which are not set correctly and cannot be queried with load schedule for shared accounts
                total_preset = str(mysite.get("retain_load", "")).replace("W", "")
                if (
                    not str(solarbank.get("set_load_power")).isdigit()
                    and total_preset.isdigit()
                ):
                    solarbank.update(
                        {
                            "parallel_home_load": f"{(int(total_preset)/len(sb_list)):.0f}",
                            "current_home_load": total_preset,
                        }
                    )
                # Work around for weird charging power fields in SB totals and device list: They have same names, but completely different usage
                # SB total charging power shows only power into the battery. At this time, charging power in device list seems to reflect the output power. This is seen for status 3
                # SB total charging power show 0 when discharging, but then device charging power shows correct value. This is seen for status 2
                # Conclusion: SB total charging power is correct total power INTO the batteries. When discharging it is 0
                # Device list charging power is ONLY correct power OUT of the batteries. When charging it is 0 or shows the output power.
                # Need to simplify this per device details and SB totals, will use positive value on both for charging power and negative for discharging power
                # calculate estimate based on total for proportional split across available solarbanks and their calculated charge power
                with contextlib.suppress(ValueError):
                    charge_calc = 0
                    power_in = int(solarbank.get("photovoltaic_power", ""))
                    power_out = int(solarbank.get("output_power", ""))
                    # power_charge = int(solarbank.get("charging_power", "")) # This value seems to reflect the output power, which is corect for status 2, but may be wrong for other states
                    charge_calc = power_in - power_out
                    solarbank["charging_power"] = str(
                        charge_calc
                    )  # allow negative values
                    sb_total_charge_calc += charge_calc
                mysite["solarbank_info"]["solarbank_list"][index] = solarbank
                new_sites.update({myid: mysite})
                # add count of solarbanks to device details and other metrics that might be device related
                if sn := api._update_dev(
                    solarbank
                    | {
                        "data_valid": data_valid,
                        "solarbank_count": len(sb_list),
                        "solar_power_1": sb_info.get("solar_power_1"),
                        "solar_power_2": sb_info.get("solar_power_2"),
                        "solar_power_3": sb_info.get("solar_power_3"),
                        "solar_power_4": sb_info.get("solar_power_4"),
                        "ac_power": sb_info.get("ac_power"),
                        "to_home_load": sb_info.get("to_home_load"),
                        "other_input_power": sb_info.get("other_input_power"),
                        "micro_inverter_power": sb_info.get("micro_inverter_power"),
                        "micro_inverter_power_limit": sb_info.get("micro_inverter_power_limit"),
                        "micro_inverter_low_power_limit": sb_info.get("micro_inverter_low_power_limit"),
                        "grid_to_battery_power": sb_info.get("grid_to_battery_power"),
                        "pei_heating_power": sb_info.get("pei_heating_power"),
                        # only passed to device for proper SB2 charge status update
                        "home_load_power": mysite.get("home_load_power"),
                    },
                    devType=SolixDeviceType.SOLARBANK.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)
                    sb_charges[sn] = charge_calc
                    # as time progressed, update actual schedule slot presets from a cached schedule if available
                    if schedule := (api.devices.get(sn, {})).get("schedule"):
                        api._update_dev(
                            {
                                "device_sn": sn,
                                "schedule": schedule,
                                "retain_load": total_preset,  # only a flag to indicate the actual schedule preset updates don't need to update site appliance load
                            }
                        )
            # adjust calculated SB charge to match total
            if len(sb_charges) == len(sb_list) and str(sb_total_charge).isdigit():
                sb_total_charge = int(sb_total_charge)
                if sb_total_charge_calc < 0:
                    with contextlib.suppress(ValueError):
                        # discharging, adjust sb total charge value in scene info and allow negativ value to indicate discharge
                        sb_total_charge = float(sb_total_solar) - float(sb_total_output)
                        mysite["solarbank_info"]["total_charging_power"] = str(
                            sb_total_charge
                        )
                for sn, charge in sb_charges.items():
                    api.devices[sn]["charging_power"] = str(
                        0
                        if sb_total_charge_calc == 0
                        else int(sb_total_charge / sb_total_charge_calc * charge)
                    )
                    # Update also the charge status description which may change after charging power correction
                    charge_status = api.devices[sn].get("charging_status")
                    if charge_status in [
                        SolarbankStatus.charge,
                        SolarbankStatus.bypass,
                        SolarbankStatus.detection,
                    ]:
                        api._update_dev(
                            {
                                "device_sn": sn,
                                "charging_status": charge_status,
                                "home_load_power": mysite.get(
                                    "home_load_power"
                                ),  # only passed for proper SB2 charge status update
                            }
                        )
            # make sure to write back any changes to the solarbank info in sites dict
            new_sites.update({myid: mysite})

            grid_info = mysite.get("grid_info") or {}
            for grid in grid_info.get("grid_list") or []:
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in grid:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    grid = dict(grid).copy()
                    grid.update({"alias_name": grid.pop("device_name")})
                if sn := api._update_dev(
                    grid
                    | {
                        "data_valid": data_valid,
                        "photovoltaic_to_grid_power": grid_info.get(
                            "photovoltaic_to_grid_power", ""
                        ),
                        "grid_to_home_power": grid_info.get("grid_to_home_power", ""),
                        "grid_status": grid_info.get("grid_status", ""),
                    },
                    devType=SolixDeviceType.SMARTMETER.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)
            smartplug_info = mysite.get("smart_plug_info") or {}
            for smartplug in smartplug_info.get("smartplug_list") or []:
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in smartplug:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    smartplug = dict(smartplug).copy()
                    smartplug.update({"alias_name": smartplug.pop("device_name")})
                if sn := api._update_dev(
                    smartplug,
                    devType=SolixDeviceType.SMARTPLUG.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)
            pps_info = mysite.get("pps_info") or {}
            for pps in pps_info.get("pps_list") or []:
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in pps:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    pps = dict(pps).copy()
                    pps.update({"alias_name": pps.pop("device_name")})
                if sn := api._update_dev(
                    pps,
                    devType=SolixDeviceType.PPS.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)
            for solar in mysite.get("solar_list") or []:
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in solar:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    solar = dict(solar).copy()
                    solar.update({"alias_name": solar.pop("device_name")})
                if sn := api._update_dev(
                    solar,
                    devType=SolixDeviceType.INVERTER.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)
            for powerpanel in mysite.get("powerpanel_list") or []:
                # work around for device_name which is actually the device_alias in scene info
                if "device_name" in powerpanel:
                    # modify only a copy of the device dict to prevent changing the scene info dict
                    powerpanel = dict(powerpanel).copy()
                    powerpanel.update({"alias_name": powerpanel.pop("device_name")})
                if sn := api._update_dev(
                    # merge powerpanel device details if available
                    powerpanel | ((api.powerpanelApi.devices.get(powerpanel.get("device_sn") or "") or {}) if api.powerpanelApi else {}),
                    devType=SolixDeviceType.POWERPANEL.value,
                    siteId=myid,
                    isAdmin=admin,
                ):
                    api._site_devices.add(sn)

    # Write back the updated sites
    api.sites = new_sites
    # update account dictionary with number of requests
    api._update_account({"use_files": fromFile})
    return api.sites


async def poll_site_details(
    api: AnkerSolixBaseApi, fromFile: bool = False, exclude: set | None = None
) -> dict:
    """Get the latest updates for additional account or site related details updated less frequently.

    Most of theses requests return data only when user has admin rights for sites owning the devices.
    To limit API requests, this update site details method should be called less frequently than update site method,
    and it updates just the nested site_details dictionary in the sites dictionary as well as the account dictionary
    """
    # define excluded categories to skip for queries
    if not exclude or not isinstance(exclude, set):
        exclude = set()
    api._logger.debug("Updating Sites Details")
    # Fetch unread account messages once and put in site details for all sites as well as into account dictionary
    api._logger.debug("Getting unread messages indicator")
    await api.get_message_unread(fromFile=fromFile)
    # refresh power panel site details if used
    if api.powerpanelApi:
        await api.powerpanelApi.update_site_details(fromFile=fromFile, exclude=exclude)
    for site_id, site in api.sites.items():
        # check if power panel site type to refresh runtime stats in sites cache
        if ((site.get("site_info") or {}).get("power_site_type") or 0) in [4]:
            api.sites[site_id]["statistics"] = (
                (api.powerpanelApi.sites.get(site_id) or {}).get("statistics") or {}
            ).copy()
        # Fetch details that only work for site admins
        if site.get("site_admin", False):
            # Fetch site price and CO2 settings
            if {ApiCategories.site_price} - exclude:
                api._logger.debug("Getting price and CO2 settings for site")
                await api.get_site_price(siteId=site_id, fromFile=fromFile)
    # update account dictionary with number of requests
    api._update_account({"use_files": fromFile})
    return api.sites


async def poll_device_details(
    api: AnkerSolixBaseApi, fromFile: bool = False, exclude: set | None = None
) -> dict:
    """Get the latest updates for additional device info updated less frequently.

    Most of theses requests return data only when user has admin rights for sites owning the devices.
    To limit API requests, this update device details method should be called less frequently than update site method,
    which will also update most device details as found in the site data response.
    """
    # define excluded device types or categories to skip for queries
    if not exclude or not isinstance(exclude, set):
        exclude = set()
    api._logger.debug("Updating Device Details")
    # Fetch firmware version of devices
    # This response will also contain unbound / standalone devices not added to a site
    api._logger.debug("Getting bind devices")
    await api.get_bind_devices(fromFile=fromFile)
    # Get the setting for effective automated FW upgrades
    if {ApiCategories.device_auto_upgrade} - exclude:
        api._logger.debug("Getting OTA update settings")
        await api.get_auto_upgrade(fromFile=fromFile)
        # Get the OTA batch info for firmware updates of owning devices
        api._logger.debug("Getting OTA update info for devices")
        await api.get_ota_batch(fromFile=fromFile)
    # Get Power Panel device specific updates
    if api.powerpanelApi:
        await api.powerpanelApi.update_device_details(
            fromFile=fromFile, exclude=exclude
        )
    # Fetch other relevant device information that requires site id and/or SN
    site_wifi: dict[str, list[dict | None]] = {}
    for sn, device in api.devices.items():
        site_id = device.get("site_id", "")
        dev_Type = device.get("type", "")

        # Fetch details that only work for site admins
        if device.get("is_admin", False) and site_id:
            # Fetch site wifi list if not queried yet with wifi networks and signal strengths
            if site_id not in site_wifi:
                api._logger.debug("Getting wifi list of site for mapping to device")
                site_wifi[site_id] = (
                    await api.get_wifi_list(siteId=site_id, fromFile=fromFile)
                ).get("wifi_info_list") or []
            # Map Wifi to usage of device if device_sn not part yet of wifi_list item
            wifi_list = site_wifi.get(site_id, [{}])
            # Ensure to update wifi index if not provided for device in scene_info, but device has wifi online and only single wifi exists in list
            if (
                not (wifi_index := device.get("wireless_type", ""))
                and len(wifi_list) == 1
                and device.get("wifi_online")
            ):
                wifi_index = "1"
                api._update_dev({"device_sn": sn, "wireless_type": wifi_index})
            # check if device_sn found in wifi_list, then it was updated already in the wifi list query, otherwise use old index method for update
            if wifi_index and not [sn for d in wifi_list if d.get("device_sn") == sn]:
                if str(wifi_index).isdigit():
                    wifi_index = int(wifi_index)
                else:
                    wifi_index = 0
                if 0 < wifi_index <= len(wifi_list):
                    api._update_dev({"device_sn": sn} | dict(wifi_list[wifi_index - 1]))

            # Fetch device type specific details, if device type not excluded

            if dev_Type in ({SolixDeviceType.SOLARBANK.value} - exclude):
                # Fetch active Power Cutoff setting for solarbanks
                if {ApiCategories.solarbank_cutoff} - exclude:
                    api._logger.debug("Getting Power Cutoff settings for device")
                    await api.get_power_cutoff(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )
                # queries for solarbank 1 only
                if ((api.devices.get(sn) or {}).get("generation") or 0) < 2:
                    # Fetch available OTA update for solarbanks, does not work for solarbank 2 with device SN
                    # DISABLED: Not reliable for Solarbank 1 either, SN can also be "", so not clear what the response actually reports
                    # api._logger.debug("Getting OTA update info for device")
                    # await api.get_ota_update(deviceSn=sn, fromFile=fromFile)
                    # Fetch defined inverter details for solarbanks
                    if {ApiCategories.solarbank_solar_info} - exclude:
                        api._logger.debug("Getting inverter settings for device")
                        await api.get_solar_info(solarbankSn=sn, fromFile=fromFile)
                    # Fetch schedule for Solarbank 1
                    api._logger.debug("Getting schedule details for device")
                    await api.get_device_load(
                        siteId=site_id, deviceSn=sn, fromFile=fromFile
                    )
                    # Fetch device fittings for device types supporting it
                    if {ApiCategories.solarbank_fittings} - exclude:
                        api._logger.debug("Getting fittings for device")
                        await api.get_device_fittings(
                            siteId=site_id, deviceSn=sn, fromFile=fromFile
                        )
                else:
                    # Fetch schedule for Solarbank 2
                    api._logger.debug("Getting schedule details for device")
                    await api.get_device_parm(
                        siteId=site_id,
                        paramType=SolixParmType.SOLARBANK_2_SCHEDULE.value,
                        deviceSn=sn,
                        fromFile=fromFile,
                    )

        # Merge additional powerpanel data
        if api.powerpanelApi:
            device.update(api.powerpanelApi.devices.get(sn) or {})

        # TODO(#0): Fetch other details of specific device types as known and relevant

        # update entry in devices
        api.devices.update({sn: device})

    # update account dictionary with number of requests
    api._update_account({"use_files": fromFile})
    return api.devices


async def poll_device_energy(
    api: AnkerSolixBaseApi, fromFile: bool = False, exclude: set | None = None
) -> dict:
    """Get the site energy statistics from today and yesterday.

    Yesterday energy will be queried only once if not available yet, but not updated in subsequent refreshes.
    Energy data can also be fetched by shared accounts.
    It was found that energy data is tracked only per site, but not individual devices even if a device SN parameter is mandatory in the Api request.
    """
    # check exclusion list, default to all energy data
    if not exclude or not isinstance(exclude, set):
        exclude = set()
    # First check if power panel sites available and use appropriate method to merge the energy stats at the end
    if api.powerpanelApi:
        await api.powerpanelApi.update_device_energy(fromFile=fromFile, exclude=exclude)
    for site_id, site in api.sites.items():
        if api.powerpanelApi and site_id in api.powerpanelApi.sites:
            # copy power panel energy stats into this sites dictionary
            site["energy_details"] = (
                api.powerpanelApi.sites[site_id].get("energy_details") or {}
            )
            api.sites[site_id] = site
        else:
            # build device types set for daily energy query, depending on device types found for site
            # solarinfo will always be queried by daily energy and required for general site statistics
            # However, daily energy should not be queried for solarbank, smartmeter or smart plug devices when they or their energy category is explicitly excluded
            query_types: set = set()
            query_sn: str = ""
            if (
                (dev_list := site.get("solar_list") or [])
                and isinstance(dev_list, list)
                and (sn := dev_list[0].get("device_sn"))
            ):
                query_types |= {SolixDeviceType.INVERTER.value}
                query_sn = sn
            if sn := (site.get("grid_info") or {}).get("device_sn"):
                query_types -= {SolixDeviceType.INVERTER.value}
                if not (
                    {
                        SolixDeviceType.SMARTMETER.value,
                        ApiCategories.smartmeter_energy,
                    }
                    & exclude
                ):
                    query_types |= {SolixDeviceType.SMARTMETER.value}
                    query_sn = sn
            if (
                plug_list := (site.get("smart_plug_info") or {}).get("smartplug_list")
                or []
            ):
                query_types -= {SolixDeviceType.INVERTER.value}
                if not (
                    {
                        SolixDeviceType.SMARTPLUG.value,
                        ApiCategories.smartplug_energy,
                    }
                    & exclude
                ):
                    query_types |= {SolixDeviceType.SMARTPLUG.value}
                    query_sn = plug_list[0].get("device_sn") or ""
            if (
                (
                    dev_list := (site.get("solarbank_info") or {}).get("solarbank_list")
                    or []
                )
                and isinstance(dev_list, list)
                and (sn := dev_list[0].get("device_sn"))
            ):
                query_types -= {SolixDeviceType.INVERTER.value}
                if not (
                    {
                        SolixDeviceType.SOLARBANK.value,
                        ApiCategories.solarbank_energy,
                    }
                    & exclude
                ):
                    query_types |= {SolixDeviceType.SOLARBANK.value}
                    query_sn = sn
                    # Query also embedded inverter energy per channel if not excluded
                    if not (
                        {
                            ApiCategories.solar_energy,
                        }
                        & exclude
                    ):
                        query_types |= {SolixDeviceType.INVERTER.value}

            if query_types:
                api._logger.debug("Getting Energy details for site")
                # obtain previous energy details to check if yesterday must be queried as well
                energy = site.get("energy_details") or {}
                # delay actual time to allow the cloud server to finish update of previous day, since previous day will be queried only once
                # Cloud server energy stat updates may be delayed by 2-3 minutes
                time: datetime = datetime.now() - timedelta(minutes=5)
                today = time.strftime("%Y-%m-%d")
                yesterday = (time - timedelta(days=1)).strftime("%Y-%m-%d")
                # Fetch energy from today or both days
                data: dict = {}
                if yesterday != (energy.get("last_period") or {}).get("date"):
                    data.update(
                        await api.energy_daily(
                            siteId=site_id,
                            deviceSn=query_sn,
                            startDay=datetime.fromisoformat(yesterday),
                            numDays=2,
                            dayTotals=True,
                            devTypes=query_types,
                            fromFile=fromFile,
                        )
                    )
                else:
                    data.update(
                        await api.energy_daily(
                            siteId=site_id,
                            deviceSn=query_sn,
                            startDay=datetime.fromisoformat(today),
                            numDays=1,
                            dayTotals=True,
                            devTypes=query_types,
                            fromFile=fromFile,
                        )
                    )
                if fromFile:
                    # get last date entries from file and replace date with yesterday and today for testing
                    days = len(data)
                    if len(data) > 1:
                        entry: dict = list(data.values())[days - 2]
                        entry.update({"date": yesterday})
                        energy["last_period"] = entry
                    if len(data) > 0:
                        entry: dict = list(data.values())[days - 1]
                        entry.update({"date": today})
                        energy["today"] = entry
                else:
                    energy["today"] = data.get(today) or {}
                    if data.get(yesterday):
                        energy["last_period"] = data.get(yesterday) or {}
                # save energy stats with sites dictionary
                site["energy_details"] = energy
                api.sites[site_id] = site
                # Add individual smart plug energy per serial also to smart plug device cache
                for plug in (energy.get("today") or {}).get("smartplug_list") or []:
                    api._update_dev(
                        {
                            "device_sn": plug.get("device_sn"),
                            "energy_today": plug.get("energy"),
                        }
                    )
                for plug in (energy.get("last_period") or {}).get(
                    "smartplug_list"
                ) or []:
                    api._update_dev(
                        {
                            "device_sn": plug.get("device_sn"),
                            "energy_last_period": plug.get("energy"),
                        }
                    )

    # update account dictionary with number of requests
    api._update_account({"use_files": fromFile})
    return api.sites
