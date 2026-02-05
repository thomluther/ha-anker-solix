<div class="container">
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/07/23/iot-admin/jvwLiu0cOHjYMCwV/picl_A17X8_normal.png" alt="Smart Plug" title="Smart Plug" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Anker MI80 Logo" title="Anker MI80" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solarbank E1600" align="right" height="80px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/opwTD5izbjD9DjKB/picl_A17X7_normal.png" alt="Smart Meter Logo" title="Anker Smart Meter" align="right" height="65px"/> </div>
  <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png" alt="Solarbank 2 E1600 Logo" title="Anker Solarbank 2 E1600"  align="right" height="80px"/> </div>
</div>

# Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![Contributors][contributors-shield]][contributors]
[![Issues][issues-shield]][issues]
[![Discussions][discussions-shield]][discussions]
[![Community Forum][forum-shield]][forum]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![License][license-shield]](LICENSE)
![python badge][python-shield]


This Home Assistant custom integration utilizes the [anker-solix Python library][anker-solix-api], allowing seamless integration with Anker Solix devices via the Anker power cloud and optionally via the Anker MQTT server. It was specifically developed to monitor the Anker Solarbank E1600. Support for further Anker devices like solar micro-inverters (MI80), Solarbank 2 E1600, Solarbank 3 E2700 and Anker smart meters has been added to the Api library and is available through the integration. The Anker power cloud also supports portable power stations (PPS), home Power Panels or home energy systems (HES) which are not or only partially supported by the power cloud. They are (or can be) integrated via the optional Anker MQTT server connection. Missing devices or features may require known Api queries or MQTT data descriptions by device owners.

> [!NOTE]
> Anker power devices which are not configured into a power system in your Anker mobile app typically do **NOT** provide any consumption data to the Anker power cloud. Likewise it has turned out, that portable power stations (PPS), power banks or power cooler do not send data to the Anker power cloud either since they are not configurable as a main power system device. Therefore, the Api library cannot get consumption data of standalone devices through the Api cloud server, but only through the optional MQTT server connection. However, most MQTT device data is published in a hex format and varies per device model, therefore it must be [decoded and described](https://github.com/thomluther/anker-solix-api/discussions/222) first by device owners.

Please refer to [supported sensors and devices](#supported-sensors-and-devices) for a list of supported Anker Solix devices.

## Disclaimer:

🚨 **This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the devices of Anker Solix power systems into their smart home. Any trademarks or product names mentioned are the property of their respective owners.** 🚨


## Usage terms and conditions:

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api, which is used by the official Anker mobile app. The cloud server Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore, the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

🚨 **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


# Table of contents

1. **[Disclaimer](#disclaimer)**
1. **[Usage terms and conditions](#usage-terms-and-conditions)**
1. **[Anker Account Information](#anker-account-information)**
1. **[Limitations](#limitations)**
1. **[Supported sensors and devices](#supported-sensors-and-devices)**
1. **[Special device notes](#special-device-notes)**
   * [Standalone inverters (MI80)](#standalone-inverters-mi80)
   * [Solarbank 1 devices](#solarbank-1-devices)
   * [Solarbank 2 devices and Smart Meters](#solarbank-2-devices-and-smart-meters)
   * [Solarbank 2 AC devices](#solarbank-2-ac-devices)
   * [Combined Solarbank 2 systems containing cascaded Solarbank 1 devices](#combined-solarbank-2-systems-containing-cascaded-solarbank-1-devices)
   * [Solarbank 3 devices](#solarbank-3-devices)
   * [Solarbank Multisystem with Power Dock](#solarbank-multisystem-with-power-dock)
   * [Solarbank station controls](#solarbank-station-controls)
   * [Electric Vehicle devices](#electric-vehicle-devices)
   * [Power Panels](#power-panels)
   * [Home Energy Systems (HES)](#home-energy-systems-hes)
   * [Other devices](#other-devices)
1. **[MQTT managed devices](#mqtt-managed-devices)**
1. **[Installation via HACS (recommended)](#installation-via-hacs-recommended)**
      * [Installation Notes](#installation-notes)
1. **[Manual installation](#manual-installation)**
1. **[Optional entity pictures](#optional-entity-pictures)**
1. **[Integration configuration and usage](#integration-configuration-and-usage)**
1. **[Issues, Q&A and other discussions](#issues-qa-and-other-discussions)**
1. **[Contributions are welcome!](#contributions-are-welcome)**
1. **[Attribution](#attribution)**
1. **[Showing Your Appreciation](#showing-your-appreciation)**
1. **[Additional Resources](#additional-resources)**
   * [Blog-Posts](#blog-posts)
   * [Videos](#videos)


## Anker Account Information

Originally, one account with email/password could not be used for the Anker mobile app and this Api in parallel. In the past, the Anker Solix Cloud allowed only one login token per account at any time. Each new login request by a client will create a new token and the previous token on the server was dropped. For that reason, it was not possible to use this Api client and your mobile app with the same account in parallel. Starting with Anker mobile app release 2.0, you could share your owned system(s) with 'family members'. Since then it was possible to create a second Anker account with a different email address and share your owned system(s) with one or more secondary accounts as member.

> [!NOTE]
> A shared account is only a member of the shared system, and as such currently has no permissions to access or query device details of the shared system.
Therefore an Api homepage query will neither display any data for a shared account. However, a shared account can receive Api scene/site details of shared systems (app system = Api site), which is equivalent to what is displayed in the mobile app on the home screen for the selected system.

> [!TIP]
> Starting end of July 2025 and with version 3.10 of the Anker mobile app, one account can now be used across multiple devices in parallel. That means active login tokens are no longer deleted upon login of another client and parallel account usage becomes possible. Actually there is **NO NEED ANYMORE** to create a second account and share the system with it, since the main account can now be used in parallel across multiple devices and clients. To switch your account, refer to [Switching between different Anker Power accounts](INFO.md#switching-between-different-anker-power-accounts)

For detailed usage instructions, please refer to the [INFO](INFO.md)


## Limitations

- The used Api library is by no means an official Api and is very limited as there is no documentation at all
- The Api library or the login can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in the underlying Api library
- The Api library was validated against both Anker cloud servers (EU and COM). Assignment of countries to either of the two servers however is unknown and depending on the selected country for your account. Upon wrong server assignment for your registered country, the Api may login but show no valid systems, devices or sensors in the integration. You need to open an issue to correct your country assignment in the Api library.
- The integration sensors and entities being provided depend on whether an Anker owner account or member account is used with the integration
- Devices may loose Wifi connection from time to time and will not be able to send data to the cloud. While device Wifi is disconnected, the reported data in the cloud may be stale. You can use the cloud state sensor of the end device to verify the device cloud connection state and recognize potentially stale data.
- MQTT data updates depend on the publish cycle of device messages. Most messages are not published regularly, but only while the real time trigger is active for the device. Therefore MQTT data may get stale, if messages are no longer published.
  - You may use the MQTT data timestamp as indicator when the last data update was received. However, this does not mean that all MQTT data were updated (it depends on the device and published message)
- If you overlay MQTT data and particular MQTT data get stale due to missing messages, the entity may not longer refresh even if the Api may provide updated data
  - You may need to automate MQTT status requests or real time triggers for the device, if certain entities no longer refresh
  - Be aware of [additional overhead](#mqtt-managed-devices) when automating 24x7 real time trigger for your devices
- The integration can support only Solix power devices which are defined in a power system via the Anker mobile app. While it may present also standalone devices that are not defined in a system, those standalone devices are not manageable through the cloud Api servers.
- Dynamic tariff and price forecast is only supported for the generic Nordpool provider. Other providers typically require registration through the mobile App and will not be supported by this integration.
- Dynamic price forecast calculations for other providers than Nordpool may be wrong, since neither the provided price unit is clear, nor whether the provider prices include fees and taxes.
- Starting with version 3.4.0, such stand alone device can be monitored through an optional MQTT server connection. However, it depends on the decoding and description of the MQTT messages for each device model whether the integration can provide useful data
- Starting with version 3.5.0, Solix devices can also be controlled via the optional MQTT server connection. However, it depends on the decoding and description of the MQTT messages and controls for each device model whether the integration can implement control entities for the device
- Further devices may be added in future once examples of Api response data or MQTT message and control descriptions can be provided to the developer.

> [!NOTE]
> To export randomized example data of your Anker power system configuration, please refer to the [anker-solix Python library][anker-solix-api] and the tool [export_system.py](https://github.com/thomluther/anker-solix-api#export_systempy). A new [HA service/action to export anonymized Api response data](INFO.md#export-systems-action) was added to the integration to simplify data collection in a downloadable zip file. You can open a new [issue as feature request](https://github.com/thomluther/ha-anker-solix/issues) and upload the zip file with the exported json files, together with a short description of your setup. You should enable the MQTT messages export option before exporting the configuration. To catch most values, the export should be run when the device is actually using many input and output channels including battery charge or discharge consumption to get meaningful data.

> [!IMPORTANT]
> The HA service/action only works if you have a valid hub configuration. Otherwise the Export System action may not be registered to HA and there may not be a functional Api target entity either for the export.

## Supported sensors and devices

This integration will set up the following HA platforms and provides support for following Anker Solix devices:

Platform | Description
-- | --
`sensor` | Show various info from Anker Solix Api.
`binary_sensor` | Show binary info from Anker Solix Api.
`switch` | Modify system or device settings via Anker Solix Api, temporary disable Api communication
`select` | Select settings from available options
`button` | Trigger device details refresh on demand
`number` | Change values for certain entities
`datetime` | Change date and time for certain entities
`service` | Various Solarbank schedule or Api related services/actions

Device type | Description
-- | --
`account` | Anker Solix user account used for the configured hub entry. It collects all common entities belonging to the account or api connection.
`system` | Anker Solix 'Power System' as defined in the Anker app. It collects all entities belonging to the defined system and is referred as 'site' in the cloud api.
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1) **(with MQTT monitoring & control)**<br>- A17C1: Solarbank 2 E1600 Pro **(with MQTT monitoring & control)**<br>- A17C3: Solarbank 2 E1600 Plus **(with MQTT monitoring & control)**<br>- A17C2: Solarbank 2 E1600 AC **(with MQTT monitoring & control)**<br>- A17C5: Solarbank 3 E2700 **(with MQTT monitoring & control)**
`combiner_box` | Anker Solix (passive) combiner box configured in the system:<br>- AE100: Power Dock for Solarbank Multisystems **(with MQTT monitoring & control)**
`inverter` | Anker Solix standalone inverter or configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Smart meter configured in the system:<br>- A17X7: Anker 3 Phase Wifi Smart Meter **(with MQTT monitoring)**<br>- SHEM3: Shelly 3EM Smart Meter<br>- SHEMP3: Shelly 3EM Pro Smart Meter **(with MQTT monitoring)**
`smartplug` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W **(with MQTT monitoring & control)**
`pps` | Anker Solix Portable Power Stations stand alone devices (only minimal Api data):<br>- A1722/A1723: C300(X) AC Portable Power Station **(MQTT monitoring & control)**<br>- A1726/A1728: C300(X) DC Portable Power Station **(MQTT monitoring & control)**<br>- A1761: C1000(X) Portable Power Station **(MQTT monitoring & control)**<br>- A1763: C1000 Gen 2 Portable Power Station **(MQTT monitoring & control)**<br>- A1780(P): F2000(P) Portable Power Station **(MQTT monitoring & control)**<br>- A1790(P): F3800(P) Portable Power Station **(MQTT monitoring & control)**
`powerpanel` | Anker Solix Power Panels configured in the system **(basic Api monitoring)**:<br>- A17B1: SOLIX Home Power Panel for SOLIX F3800 power stations (Non EU market)
`hes` | Anker Solix Home Energy Systems and their sub devices as configured in the system **(basic Api & MQTT monitoring)**:<br>- A5101: SOLIX X1 P6K US<br>- A5102 SOLIX X1 Energy module 1P H(3.68-6)K<br>- A5103: SOLIX X1 Energy module 3P H(5-12)K<br>- A5220: SOLIX X1 Battery module
`vehicle` | Electric vehicles as created/defined under the Anker Solix user account. Those vehicles are virtual devices that will be required to manage charging with the announced [Anker Solix V1 EV Charger](https://www.ankersolix.com/de/smart-ev-ladegeraet-solix-v1) (🇩🇪).

For more details on the Anker Solix device hierarchy and how the integration will represent them in Home Assistant, please refer to the discussion article [Integration device hierarchy and device attribute information](https://github.com/thomluther/ha-anker-solix/discussions/239).


## Special device notes

### Standalone inverters (MI80)

Anker does not support the creation of a power system with their MI80 inverter as main and only device. However, the solar power and energy yields are still reported and tracked in the cloud and can be monitored in the mobile app. Version 2.7.0 added support for such standalone inverters. Even the persistent inverter limit can be changed via the cloud api. In order to merge entities for standalone inverters with the [common integration device hierarchy](https://github.com/thomluther/ha-anker-solix/discussions/239), a virtual system (site) will be created by the api library as home for the data polling and all entities that are typically related to a system device. The cloud update interval is approximately every 60 seconds if the inverter is online. The api however does a false reporting of the inverter Wifi state, which is always reported offline independent of its real Wifi state. The cloud connection state is a better indicator whether the inverter is On or Off. Since standalone inverters cannot be added to a real Anker power system, their monitoring cannot be shared with other accounts and their usage is limited to the Anker account that owns the device.

> [!IMPORTANT]
> It is assumed that any inverter limit change will be applied to persistent memory in the hardware. Write cycles are limited by the hardware, therefore it is **NOT recommended to modify the limit permanently** for any kind of output regulation. The limit change is currently not supported if the inverter is part of a solarbank system since the [api functionality still has to be verified by such system owners](https://github.com/thomluther/ha-anker-solix/discussions/255).


### Solarbank 1 devices

Solarbank 1 systems transfer their power values every 60 seconds to the cloud while there is PV generation or battery discharge. Once the Solarbank 1 goes into standby mode, there is only a cloud state check/update once per hour to save standby energy consumption.

> [!NOTE]
> If you want to use the output preset through the integration, you need to be aware of an Api bug that disables the export completely (set to 0 W) which is not possible via the Anker app at all. This occurs if the Api sends only a single slot (e.g. full day) in the schedule. This problem can only be fixed if you apply another plan change via the mobile app. To utilize the output preset without issues, you need to make sure that your schedule plan has at least 2 time slots.

> [!IMPORTANT]
> The daily battery discharge statistic value for Solarbank 1 is no longer correct since mid June 2024. The cloud statistics changed this value when introducing support for Solarbank 2. The daily battery discharge value for Solarbank 1 now includes also bypassed PV energy, so its value is no longer dedicated to battery discharge only. You can see this wrong value also in your Anker app statistics for the Solarbank 1 battery.

Version 3.4.0 added comprehensive [device MQTT data](#mqtt-managed-devices) as new entities or attributes to existing entities.

Version 3.5.0 added device control via optional MQTT connection. This is implemented via additional or hybrid control entities.


### Solarbank 2 devices and Smart Meters

Anker changed the data transfer mechanism to the Api cloud with Solarbank 2 power systems. While Solarbank 1 systems transfer their power values every 60 seconds to the cloud, Solarbank 2 systems seem to use different intervals for their data updates to the cloud which is either 5 minutes or few seconds. Originally this resulted in **invalid data responses and unavailable entities** for shared accounts or api connections. This problem was resolved by Anker, but the regular cloud update interval remains at 5 minutes. Please see the [configuration option considerations for Solarbank 2 systems](INFO.md#option-considerations-for-solarbank-2-systems) in the [INFO](INFO.md) for more details and how you can avoid unavailable entities if this problem should occur again.

> [!IMPORTANT]
> Any change of the control entities is typically applied immediately to Solarbank devices. However, since all Solarbank 2 devices have only a cloud update frequency of 5 minutes, it may take up to 6 minutes until you see the effect of an applied change in other integration entities (e.g. in various power sensors).

Version 3.4.0 added [device MQTT data](#mqtt-managed-devices) as new entities or attributes to existing entities.

Version 3.5.0 added device control via optional MQTT connection. This is implemented via additional or hybrid control entities.

> [!IMPORTANT]
> The output limit change via the integration may not work properly since the required Api request is unknown at this time. See more details in [Solarbank station controls](#solarbank-station-controls)


### Solarbank 2 AC devices

The Solarbank 2 AC model comes with new and unique features and initial support has been implemented with version 2.5.0. Version 2.6.0 added support for missing capabilities like modifications of the Time of Use plan via control entities or actions.

> [!NOTE]
> The Solarbank 2 AC devices still have issues and may stop updating some values in the cloud after active use of the mobile app with the system owner. See issue [#211](https://github.com/thomluther/ha-anker-solix/issues/211#issuecomment-2692936285).

Version 3.4.0 added [device MQTT data](#mqtt-managed-devices) as new entities or attributes to existing entities.

Version 3.5.0 added device control via optional MQTT connection. This is implemented via additional or hybrid control entities.

> [!IMPORTANT]
> The output limit change via the integration may not work properly since the required Api request is unknown at this time. See more details in [Solarbank station controls](#solarbank-station-controls)


### Combined Solarbank 2 systems containing cascaded Solarbank 1 devices

This coupling feature for 1st generation Solarbank devices was [announced in May 2024](https://www.ankersolix.com/de/blogs/balkonkraftwerk-mit-speicher/solarbank-der-ersten-generation-und-solarbank-2-pro-zusammen-fur-mehr-energiekontrolle) and [delivered in Dec 2024](https://www.ankersolix.com/de/blogs/balkonkraftwerk/die-1-generation-der-solarbank-vereint-sich-mit-dem-energiesystem-der-solarbank-2-pro-plus).
It turns out that Anker implemented just the bare minimum to support such combined systems. As users noticed, the power totals and energy statistics for such systems reflect ONLY the SB2 data, but not any SB1 data. That means you don't see anymore the SB1 solar power / energy during the day, but the SB1 discharge at night counts as solar power/energy of the SB2 during the night. All reported charge or discharge data does not reflect anything of the SB1 devices in the system. So the SB1 is pretty much a black box for the Anker home page and the energy statistics, which can also be accessed by system members.
Furthermore, the SB1 device(s) may have different schedules in combined systems. While the SB2 is running in an automatic mode, the SB1 has its own schedule with all known controls for any number of time intervals. When the SB2 is switched to manual mode however, it enforces another, minimalistic all day interval schedule to the SB1 devices which is not accessible via the mobile App. This schedule has no interval control elements. The output preset is the only value for the whole day interval and it is determined by the SB2, depending on its manual plan settings and SOC. When adding a SB1 device into a SB2 system, the 'Solarbank 2' will get configured as inverter type for the cascaded SB1 device. Therefore the output preset in this minimalistic schedule can also be 0 W for the SB1, however the 0 W output will only be applied if the 0 W output switch accessory is installed between SB1 output and SB2 input. Otherwise the SB1 will still bypass a minimum of 100 W typically. To prevent any SB1 schedule modifications while the enforced schedule is active, the integration will make all affected control entities unavailable to prevent user changes. Therefore you may see unavailable controls in cascaded SB1 devices that cannot be modified any longer, otherwise this may screw up the presented values and schedule settings, which would always be applied to the real SB1 schedule, even if inactive.
To present correct total values for the combined system, the Api library corrects also the solarbank totals in the Api system info response based on proper accumulation of individual solarbank device values:
  - Total solar power: SB1 device(s) solar power + SB2 device solar power - SB1 device(s) output power
  - Total output power: Remains SB2 device output power
  - Total SOC: Weighted average SOC across all devices, considering also number of SB2 battery packs
  - Total battery power:
    - The device battery power has always been calculated by the library, since the Api never reflected reliable charge or discharge power fields
    - It is calculated as Solar power - Output power, resulting in the overall battery power for the device (positive charge power and negative discharge)
    - Since a single device cannot charge and discharge at the same point in time, the device battery power typically reflects the complete charge OR discharge power
    - The total battery power simply accumulates each device's battery power, and thus reflecting the total NET battery power
    - However, this total NET battery power of multiple devices cannot reflect the total charge or discharge power at any given time, since a SB1 discharge of 100 W and a charge of those 100 W by the SB2 will result in 0 W NET battery power. So neither the 100 W charge power nor the 100 W discharge power are reflected in the total (NET) battery power value.

> [!IMPORTANT]
> If you derived your HA energy integral sensors or other helpers from a positive/negative value split of the system battery power, your charge and discharge energy calculations will not be accurate anymore in combined systems.

To achieve a correct charge and discharge energy calculation for your energy dashboard, you need to separate the charge and discharge power individually from each device battery power value. Then you can accumulate correct energies in following 2 ways:
  - Accumulate charge and discharge energy individually for each device and add them all to the energy dashboard. This allows granular energy tracking per Solarbank, since the dashboard will automatically accumulate energies of same type, but display each in a different color. This is the recommended option.
  - Create total charge and discharge power helper entities, that summarize the device power values separately. Then you can accumulate the total charge and discharge energies from those new summary helper entities.


### Solarbank 3 devices

Solarbank 3 devices behave similar to Solarbank 2 AC devices, but they will provide additional entities and usage mode options that are unique to this generation:
  - Anker Intelligence (AI) usage with 'Smart' mode
  - Dynamic Price support (Provider options depend on country and model)
  - New 'Time Slot' usage mode (based on dynamic prices) to automate AC charging and discharging
  - 24h solar forecast data while 'Smart' mode is active, which can be seen in the App intraday solar chart

However, it was noticed that the Solarbank charging status code is not longer being used by models that contain a hybrid inverter (since Solarbank 2 AC). The code remains always '0' which is translated into a `Detection` status as used by earlier solarbank models. Since that is no longer meaningful for Solarbank 2+ models, starting with version 3.2.0 an appropriate charging status description is assumed for code '0' of Solarbank 2+ devices, which is based on the actual power and SOC value constellation. A new description for AC charging was also implemented to better distinguish the various charging modes for hybrid inverter models.

> [!IMPORTANT]
> Neither 'Smart' mode nor 'Time Slot' mode configuration options are provided in the known cloud Api structures. Therefore these new modes can only be toggled, but not configured or modified via the integration. If you want the toggle to these new modes, they must be configured initially through the mobile app. For example, the Smart mode requires your data usage authorization as well as confirmation of device location via Google Maps before it can be enabled.

[Dynamic utility rate plan support](INFO.md#dynamic-utility-rate-plans-options) was introduced with integration version 3.0.0. Version 3.1.0 added support for [solar forecast data](INFO.md#solar-forecast-data).

> [!NOTE]
> The Solarbank 3 dynamic price VAT and fee actually cannot be determined or modified through the cloud Api. While those entities can be customized in the integration, the changes are only applied as customization to the Api cache, but **NOT** to your real system configuration. However, they are required to calculate the total dynamic prices (actual and forecast) as used by your system to evaluate charge and discharge slots as well as saving calculations. To monitor total dynamic prices and forecast also as system member, those entities have been made customizable in the Api cache for now. They will be initialized with an average default for your country if defined. Refer to [customizable entities](INFO.md#customizable-entities-of-the-api-cache) for more details on their behavior.

Version 3.4.0 added [device MQTT data](#mqtt-managed-devices) as new entities or attributes to existing entities.

Version 3.5.0 added device control via optional MQTT connection. This is implemented via additional or hybrid control entities.

> [!IMPORTANT]
> Following limitations apply:
- The output limit control via the integration may not work properly since the required Api request is unknown at this time. See more details in [Solarbank station controls](#solarbank-station-controls).
- Dynamic price forecast support remains limited to the Nordpool provider only. **Other price providers may show wrong price calculations**, see [Dynamic price provider selection](#dynamic-price-provider-selection).


### Solarbank Multisystem with Power Dock

Anker announced the [Solarbank Multisystem solution for early testing in Germany](https://www.ankersolix.com/de/balkonkraftwerk-mit-speicher/solarbank3-a17c5-multisystem) (DE) with common delivery planned in September 2025. A Solarbank Multisystem with the Power Dock will support up to 4 Solarbank devices. Initially this is only supported for Solarbank 3, but the various Solarbank 2 models are announced to follow end of 2025.

> [!IMPORTANT]
> Actually there are significant consumption data update issues for such systems during the initial deployment phase and cloud values may be wrong or lagging hours behind. This becomes especially visible via the Api or the Anker mobile App once using a member account.

The Api library implemented enhancements to mask some value errors, but this can be done only on a limited base. It also does not help for proper total value breakdown to individual devices, if the breakdown is missing in the cloud data. Therefore some of the Solarbank device power values may reflect the appliance totals instead of individual breakdown.
Many settings for Multisystems are shared across all Solarbanks in the system, like usage mode, SOC reserve and export to grid setting. In the mobile App they are managed through the station settings, and the individual device settings are greyed out. Custom plans for output presets is shared for all devices, and the individual device output is managed automatically across all solarbanks, depending on their SOC, capacity etc. That means they cannot be modified individually anymore.
Starting with version 3.5.0, the integration consolidates all merged device settings in the Power Dock device and individual device controls are no longer available. The new combiner box device type will be used for the Power Dock device, and it will reflect combined sensors and control entities for such Multisystems, although those values and settings may not managed by the combiner box itself, but via Api controls or hybrid Api and MQTT controls across all devices.

> [!NOTE]
> The expected Multisystem support for Solarbank 2 devices or intermix required a new system type, that allows combining parallel and different SB2 types within a system. This may be reflected in different Api structures compared to SB3 Multisystems (which may not need a Power Dock), and it is unclear whether the integration can support SB3 Multisystems without Power Dock with the recent 3.5.0 changes.
> For more details on Multisystem support, please refer and contribute to issue [#310](https://github.com/thomluther/ha-anker-solix/issues/310)

Version 3.4.0 added [device MQTT data](#mqtt-managed-devices) as new entities or attributes to existing entities for Power Docks that are connected to the cloud.

Version 3.5.0 added device control via optional MQTT connection and merged individual solarbank device controls to Power Dock controls. Multisystem controls are implemented via additional or hybrid control entities.

> [!IMPORTANT]
> The output limit for Multisystems is not changeable via the integration since the required Api request is unknown at this time. See more details in [Solarbank station controls](#solarbank-station-controls)


### Solarbank station controls

Device controls via station controls have been implemented by Anker to manage Solarbank devices that may support Multisystem configurations (with or without Power Dock). The station provides the capability to manage a system or device control in a central place, that may have to be applied to one or more devices in parallel. The station control settings that you can find in the mobile app typically must be changed through the cloud Api, while the individual devices settings on the device details panel typically reflect the MQTT values (if it is an MQTT control). If a device control is managed centrally by the station, it is typically greyed out on the device panel, but you can still see the active setting based on MQTT data of the device. As it turned out, some of the station controls cannot be managed by the Api alone, if the cloud does not distribute the required MQTT commands to the dependent devices. On the other hand, if only the device MQTT commands are distributed by a client, the settings on the station panel will not change, and the cloud may not be aware of station control changes. Various controls shown on the station panel require various (hybrid) Api and/or MQTT control. This hybrid control is now implemented in the integration if the MQTT connection is enabled. Otherwise you may not see those MQTT dependent controls anyway.

Following settings may require the hybrid approach:
- SOC reserve (min SOC) - same for all Solarbank devices in Multisystems, must also be set on Power Dock device
- PV input limit - individual per Solarbank
- AC input limit (AC charge limit) - individual per Solarbank
- AC output limit (max home load) - overall limit across all Solarbank devices in system, must also be set on Power Dock device
  - This control has limited support through the integration
  - It may work for single solarbank systems (but station display does not change)
  - It is not changeable for Multisystems
- Grid export switch - same for all Solarbank devices in Multisystems, must also be set on Power Dock device
  - Grid export limit 100-100000 W - same for all Solarbank devices in Multisystems, must also be set on Power Dock device (requires FW that supports the limit setting)
- 3rd party PV switch - same for all Solarbank devices in Multisystems, must also be set on Power Dock device and is typically cloud driven
  - This will not be implemented to the integration, since it depends on FW and is typically a one time system configuration setting that does not need automation
- EV charger enablement switch - same for all Solarbank devices in Multisystems, must also be set on Power Dock device and is typically cloud driven
  - This will not be implemented to the integration, since it depends on FW and is typically a one time system configuration setting that does not need automation

> [!IMPORTANT]
> The Api query to change the AC output limit (max home load) on the station panel is unknown. Therefore this control may not fully work for single systems, altough the device itself will show the limit change being applied through MQTT. For Multisystems, the output limit therefore cannot be changed through the integration, since that is controlled through the cloud server with regular MQTT commands across all Solarbanks and the Power Dock. This control cannot be supported by the integration until someone will find the required Api query/parameters to change the output limit for Solarbank devices. More details are discussed in this [issue comment](https://github.com/thomluther/anker-solix-api/issues/216#issuecomment-3804889623) in case you want to contribute.


### Electric Vehicle devices

Anker announced its [Solix V1 EV Charger](https://www.ankersolix.com/de/smart-ev-ladegeraet-solix-v1) (DE) which can be used as stand alone system or being integrated into the X1 HES system as well as into the Solarbank Multisystem (by 4Q 2025). The EV Charger device can be shared amongst Anker cloud users, while each user can define/create its own virtual electric vehicle, or even multiple of them (up to 5 vehicles per account). The vehicles are used to manage EV charging by individual users, even if they are not the owner of the system to which the EV Charger device belongs to. Each user will need to create its own vehicle(s) to create and manage charge orders for the V1. The integration currently does **NOT** support the vehicle creation itself, but it creates a virtual device for each existing EV under the user account and it can modify various vehicle attributes and show all entities that belong to the vehicle. The user vehicle can also be deleted by removing the vehicle device from the integration hub.

> [!TIP]
> The integration will automatically discover added and remove vehicles under the user account during the regular device details refresh cycle (10 minutes per default). An immediate vehicle refresh can also be triggered manually by a corresponding button of the account device.


### Power Panels

Power Panels are not supported in the EU market, therefore the EU cloud api server currently does not support either the required endpoints. Furthermore it was discovered that the F3800 power stations attached to the Power Panel are not tracked as system devices. Actual power consumption data in the cloud api was not discovered yet and it is assumed that the power panel home page consumption values are merged by the App from the MQTT cloud server only if the App home page is viewed. A work around for monitoring some power values and overall SOC has been implemented by extracting the last valid 5 minute average data that is collected with the system energy statistics (Basically the last data point that is visible in the various daily diagrams of your mobile app). However this comes with a **[cost of ~80 MB data traffic per system per day](https://github.com/thomluther/ha-anker-solix/discussions/32#discussioncomment-12748132)** just for the average power values. You can exclude the average power category from your integration configuration options to reduce they daily data traffic.

Integration version 3.1.0 added a [customizable battery capacity](INFO.md#battery-capacity) to the Powerpanel device. Since the assigned F3800 PPS cannot be determined via Api queries, the capacity is assumed with a single F3800 device without expansion batteries. You can adjust the capacity to your installation to let the integration calculate the estimated remaining battery energy based on the actual SOC. See [customizable entities](INFO.md#customizable-entities-of-the-api-cache) for a better understanding how such virtual entities are being used.

Power Panel owners need to explore and document cloud Api capabilities to further expand any Power Panel system or device support. Please refer to issue [Add F3800/BP3800 Equipment when connected to Home Power Panel](https://github.com/thomluther/anker-solix-api/issues/117) for contribution.

Version 3.4.0 added [device MQTT data](#mqtt-managed-devices) for F3800(P) device that are typically attached to power panels.

Version 3.5.0 added device control via optional MQTT connection for F3800(P) devices.


### Home Energy Systems (HES)

Anker released also large battery devices to complement existing PV systems. They are classified as Home Energy Systems (HES) and they come along with their own Api structures and endpoints. The X1 system belongs to this device category. The common HES Api structures and information is still unknown to a large extend, since most queries require owner access to such a device. Furthermore no endpoint to query actual power values has been identified yet, and it is assumed that the power values presented on the App home screen are merged from the MQTT server Api, but only when the App is actively used. In order to provide initial monitoring capabilities similar to Power Panel systems, the same work around for average power values and overall SOC has been implemented by extracting the last valid 5 minute average data that is collected with the system energy statistics (Basically the last data point that is visible in the various daily diagrams of your Anker App). However this comes with a **[cost of ~80 MB data traffic per system per day](https://github.com/thomluther/ha-anker-solix/discussions/32#discussioncomment-12748132)** just for the average power values. You can exclude the average power category from your integration configuration options to reduce they daily data traffic.

Since integration version 3.0.0, a customizable battery capacity entity was implemented for each X1 battery module. As described above, SOC and average power values are extracted from intraday energy stats of the whole system. The values are reported against the main controller device in your system. Likewise this controller device has now also a virtual and customizable capacity entity for the whole system. If you adjust the capacity of individual battery modules, this is considered automatically for the overall system capacity calculation. However, if you modify the overall system capacity in the main controller device, individual capacity modifications of battery modules are ignored.

Integration version 3.1.0 added [Dynamic utility rate plan support](INFO.md#dynamic-utility-rate-plans-options) to monitor dynamic price forecasts for your system. However, none of those entities can actually control your X1 system settings, they are only used as [customizable entities](INFO.md#customizable-entities-of-the-api-cache) to calculate the total energy price.

X1 system owners need to explore and document cloud Api capabilities to further expand any X1 system or (sub-)device support. Please refer to issue [Extending the solution to support Anker Solix X1 systems](https://github.com/thomluther/anker-solix-api/issues/162) for contribution or create a new and more specific issue as feature request.

> [!NOTE]
> The X1 devices report also MQTT data, but their format is a json string with abbreviated field names and unknown context. You need to use the mqtt_monitor tool and describe the json fields appropriately in [this issue](https://github.com/thomluther/anker-solix-api/issues/162) for proper data extraction and usage in the HA integration.

Version 3.5.2 added experimental [device MQTT data](#mqtt-managed-devices) for X1 primary controller modules. This version also changed the capacity calculations per controller, which now only reflects the (customized) capacity of the battery modules they control. For larger systems with multiple controllers, there will only be one primary controller that is used as home for all entities. This also seems to be the only device that reports MQTT messages. Any overall SOC and Battery Energy calculation will be assigned to the primary controller device.

> [!TIP]
> If you prefer local integration of your X1 devices, please refer to the generic [HA Modbus integration](https://www.home-assistant.io/integrations/modbus/) and the [Anker X1 Modbus specification](https://support.ankersolix.com/de/s/download-preview?urlname=Anker-SOLIX-X1-Series-Modbus-Protocol). Modbus will NOT be covered by this project, and you need to configure the Modbus integration in YAML, including each sensor definition according to the documented modbus registers. Examples are shown by user [@Freacly](https://github.com/Freacly) in this [issue](https://github.com/thomluther/ha-anker-solix/issues/429#issuecomment-3810556184).


### Other devices

Other devices not listed in the support table are neither supported nor tested with the Api library or the HA integration. Be aware that devices are only supported by the Anker cloud Api if they can be added into a Power System. Stand alone devices such as portable power stations (PPS), power charger or power cooler, can only be controlled through the MQTT server, and therefore require usage of the owner account and a description for all relevant MQTT message and command types that are being used by each particular device model.

To get additional Anker power devices/systems added, please review the [anker-solix Python library][anker-solix-api] and contribute to [open issues](https://github.com/thomluther/anker-solix-api/issues) or Api exploration. Most devices can neither be tested by the developer, nor can they be added to the HA integration before their Api usage, parameters, structures and fields are fully understood, interpreted and implemented into the Api library.
You can also explore the Anker Solix cloud Api directly within your HA instance via the integration's [Api request action](INFO.md#api-request-action).
The same applies to [MQTT managed devices](#mqtt-managed-devices), since decoding and description/interpretation of values requires real time monitoring of the messages under various conditions while comparing the decoded values with App data.

> [!IMPORTANT]
> While the integration may show standalone devices that you can manage with your Anker account, the cloud Api used by the integration does **NOT** contain or provide power values or much other details from standalone devices which are not defined to a Power System, typically since the do not require a holistic system view with a group of devices and the Api cloud does not track or provide energy statistics for those devices either. The real time data that you see in the mobile app under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their real time values but only for the time they are triggered by an owner account in the App. Such data can only be integrated via the optional MQTT server connection.


## MQTT managed devices

Since integration version 3.4.0, an additional connection to the Anker MQTT Server can be utilized to monitor (and control with a later version) any of the Anker Solix devices that you own in your account in the same way as you can monitor and control them in the Anker mobile app. However, since MQTT messages and commands are encoded and may differ for each device model, they have to be decoded and described first before your device can be supported. For already described devices, you may see additional entities being created beside the limited standard Api entities, which are updated as MQTT messages with their date are published by the device. Anker Solix devices are using different types of MQTT messages, reporting them at different intervals and with different content. Not every created entity will be updated with each message. Furthermore, there are also special messages that are only sent if the device is triggered to publish real time data. Real time messages are typically published in 3-5 second intervals to the MQTT server, but only while the real time trigger is active for the device.

The integration also supports a button per MQTT managed device that can be used to trigger real time data of the device with a common timeout that can be configured in the MQTT options of your hub. If the device will receive any trigger command, the timeout used in the last trigger command will be applied. The app typically uses timeouts of 300 seconds, which is also the default timeout of the integration.

Integration version 3.4.1 added another button for a single MQTT status request. If fully supported by the device, it will send one set of status message(s) that are otherwise only sent if the real time trigger is active. However, devices may also send only the main status message without optional extra status messages, which may be provided only if the real time trigger is active.

> [!NOTE]
> Anker has no consistent implementation across their Solix devices whether they publish all status messages upon a single status request. Especially Solarbank 2 and later, as well as Multisystem constellations have many extra status messages that are only published while the **real time trigger** is active.

Depending on how devices publish their data in regular, status request or real time trigger messages, you may need to automate the real time trigger to keep all MQTT based entities updating their states. Otherwise, entities with data that is only available in real time messages will get stale, if the real time data publish will timeout. The integration provides two buttons for each eligible device and you can control status requests or real time triggers for your customized needs via an automation that will press any of the buttons at regular intervals, or only under certain conditions which you can define in your automation. The integration does not limit how often or how many real time trigger or status request commands are being sent, so you have maximum flexibility for receiving MQTT data of your devices.

> [!IMPORTANT]
> Be aware that real time data may come with a cost if triggered permanently:
> - There will be larger amounts of traffic to your HA server but also between the devices and the Anker MQTT and cloud servers
> - The Anker cloud infrastructure may not be scalable enough to maintain such 24x7 real time traffic for growing number of devices, since that is no use case with normal mobile App usage
> - The devices may be kept awake and never go to sleep mode, therefore using more power than necessary
>
> For those reasons, the trigger is only a button that satisfies the MQTT real time data trigger command and it will not be provided as permanent switch control. I would not recommend permanent trigger usage either, unless you have no other choice to receive desired device data updates permanently.

Integration version 3.5.0 added control entities for MQTT manageable devices. If the various MQTT commands for the device model have been decoded and described by the community, the integration can now control those devices as well and provide similar management experience as the mobile app.

> [!IMPORTANT]
> Most of those controls cannot be validated by the developer since they require owner access to the real device type. Use the controls with care and validate them appropriately. You may open an issue with a system export and you have to use the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) to analyse the MQTT commands from your mobile app for debugging and problem fixing.

For more details on MQTT usage and hybrid integration, please refer to [MQTT connection and integration](INFO.md#mqtt-connection-and-integration).

If you don't find any useful new data for your owned devices although you enabled the MQTT server connection, your device model still has to be decoded and described. You can contribute by starting with the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) from the [Api library](https://github.com/thomluther/anker-solix-api) and follow the [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222). In order to decode MQTT commands of your device, please follow this [MQTT command and state analysis and description](https://github.com/thomluther/anker-solix-api/discussions/222#discussioncomment-14660599).


## Installation via HACS (recommended)

🎉 The repository has been added to HACS community store 🎉

You should find the Anker Solix integration when you search for Anker Solix in HACS and you can install it directly from your HACS store.

Unfortunately, HACS does not automatically install the optional entity images that must be located within the web accessible `www` folder, which must be located in your HA installation configuration folder. Please see [Optional entity pictures](#optional-entity-pictures) for instructions to copy the image files manually.

If you don't find the integration in your HACS store, use this button to add the repository to your HACS custom repositories:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-install]

Or use following procedure for HACS 2.0 or later to add the custom repository:
1. Open the [HACS](https://hacs.xyz) panel in your Home Assistant frontend.
1. Click the three dots in the top-right corner and select "Custom Repositories."
1. Add a new custom repository via the Popup dialog:
   - **Repository URL:** `https://github.com/thomluther/ha-anker-solix`
   - **Type:** Integration
1. Click "Add" and verify that the `Anker Solix` repository was added to the list.
1. Close the Popup dialog and verify that `Anker Solix` integration is now listed in the Home Assistant Community Store.
1. Install the integration


### Installation Notes

- It was observed that adding the repository to HACS via the button, an error may occur although it was added. You may check if you can find Anker Solix listed as possible HACS integration to be installed. If not, try to add the repository again.
- After adding the custom repository and installing the integration under HACS, you must restart Home Assistant to pick up the changes in your custom integration folder
   - HA 2024.02 will report the required restart automatically under problems
- After HA restart, you can install and configure the integration like a normal core integration via the HA frontend:
   - Go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix". It should now be listed as community integration


## Manual Installation

1. Using the tool of choice to open the directory (folder) for your HA configuration (where your `configuration.yaml` is located, e.g. `/homeassistant`)
1. If you do not have a `custom_components` directory (folder) there, you need to create it
1. In the `custom_components` directory (folder) create a new folder called `anker_solix`
1. Download _all_ the files from the `custom_components/anker_solix/` directory (folder) in this repository
1. Place the files you downloaded in the new directory (folder) you created
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix"


## Optional entity pictures

If you want to use the optional entity pictures that are shown in the example screenshots in the [INFO](INFO.md), you need to copy the `images` folder from the integration installation path to the `www` folder of your Home Assistant installation configuration folder. If you operate a Home Assistant OS device, you can preferably use file management Add Ons such as Studio Code Server or File Explorer to copy this folder after the installation:
1. Navigate to the configuration folder of your HA installation (where your `configuration.yaml` is located, e.g. `/homeassistant`)
1. Navigate to `custom_components/anker_solix/` folder and copy the `images` subfolder containing the entity pictures
1. Go back to your configuration folder and navigate to or create the `www/community/anker_solix` folder structure if not existing
1. Paste the `images` folder into the created `anker_solix` community subfolder

 Once the images are available in `www/community/anker_solix/images/`, they will be picked up when the integration is (re-)creating the entities, like on first creation or re-load of the configuration entry.  Make sure to reload your HA UI browser window without cache to get the entity pictures displayed correctly.

> [!IMPORTANT]
> If you just created the `www` folder on your HA instance, it is not mapped yet to the `/local` folder and cannot be accessed through the browser. You have to restart your HA instance to have the new `www` folder mapped to `/local` and allow the entity pictures to be displayed.


## Integration configuration and usage

For detailed instructions on how to configure and use the integration, please refer to [INFO](INFO.md).

Note: When you make changes to the integration folder content, you need to restart Home Assistant to pick up those changes for the container or virtual environment where Home Assistant is being started. This is applicable as well when the integration is updated manually or via HACS.


## Issues, Q&A and other discussions

If you have a problem, [review existing issues or open a new issue](https://github.com/thomluther/ha-anker-solix/issues) with detailed instructions describing the problem. You may need to enable Debug Output for your Integration configuration. Review your debug output before you post it. While sensitive login information is masked, your unique device information as returned from the Api is not masked (serial numbers, IDs etc). You may want to change that globally before providing a debug output.

If you have questions, observations, advises or want to share your experience, feel free to open a new [discussion topic](https://github.com/thomluther/ha-anker-solix/discussions).


## Contributions are welcome!

If you want to contribute to this project, please read the [Contribution guidelines](CONTRIBUTING.md).
As a starter, you may want to add more [translations](https://github.com/thomluther/ha-anker-solix/discussions/12) for your native language.
If you have no Python knowledge, you can contribute by exploring the Anker Solix Api via the [Api request action](INFO.md#api-request-action) and document your discovery of new, unknown Api request capabilities and information about your owned Anker Solix devices that you still miss in the integration.
If you don't find any data for your owned devices although you enabled the MQTT server connection, your device model still has to be decoded and described. You can contribute by starting with the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) from the [Api library](https://github.com/thomluther/anker-solix-api) and follow the [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222). In order to decode MQTT commands of your device, please follow this [MQTT command and state analysis and description](https://github.com/thomluther/anker-solix-api/discussions/222#discussioncomment-14660599).


## Attribution

- [anker-solix-api library][anker-solix-api]
- [solix2mqtt project](https://github.com/tomquist/solix2mqtt)
- [Solaredge HA core integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/solaredge)
- [ha-hoymiles-wifi custom integration](https://github.com/suaveolent/ha-hoymiles-wifi)


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/ha-anker-solix
[anker-solix-api]: https://github.com/thomluther/anker-solix-api
[releases]: https://github.com/thomluther/ha-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/ha-anker-solix.svg?style=for-the-badge
[issues]: https://github.com/thomluther/ha-anker-solix/issues
[issues-shield]: https://img.shields.io/github/issues/thomluther/ha-anker-solix.svg?style=for-the-badge
[discussions]: https://github.com/thomluther/ha-anker-solix/discussions
[discussions-shield]: https://img.shields.io/github/discussions/thomluther/ha-anker-solix.svg?style=for-the-badge
[contributors]: https://github.com/thomluther/ha-anker-solix/contributors
[contributors-shield]: https://img.shields.io/github/contributors/thomluther/ha-anker-solix.svg?style=for-the-badge
[buy-me-coffee]: https://www.buymeacoffee.com/thomasluthe
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-install]: https://my.home-assistant.io/redirect/hacs_repository/?owner=thomluther&repository=https%3A%2F%2Fgithub.com%2Fthomluther%2Fha-anker-solix&category=Integration
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/ha-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange


## Additional Resources

- [Usage instructions and configuration of the integration](INFO.md)
- [Possibilities to integrate the Solarbank into your Energy Dashboard](https://github.com/thomluther/ha-anker-solix/discussions/16)
- [Surplus charge automation for Solarbank E1600 (1st generation)](https://github.com/thomluther/ha-anker-solix/discussions/81)
- [How to monitor Solarbank battery efficiency and health](https://github.com/thomluther/ha-anker-solix/discussions/109)

If you need more assistance on the topic, please have a look at the following external resources:

### Blog-Posts

- [simon42 - Anker Solix – Home Assistant Energiedashboard & Steuerung](https://www.simon42.com/anker-solix-home-assistant/)  (🇩🇪)
- [Alkly - Anker SOLIX Balkonkraftwerk & Home Assistant integrieren](https://alkly.de/anker-solix-in-home-assistant/)  (🇩🇪)
- [Alkly - Anker Integration in Home Assistant einrichten – Eine Schritt-für-Schritt-Anleitung](https://alkly.de/anker-integration-in-home-assistant-einrichten-eine-schritt-fuer-schritt-anleitung/)  (🇩🇪)

### Videos

#### YouTube-Video "Anker SOLIX in Home Assistant integrieren" (🇩🇪)

[![Anker SOLIX in Home Assistant integrieren](https://img.youtube.com/vi/66jbUnKnkSA/mqdefault.jpg)](https://www.youtube.com/watch?v=66jbUnKnkSA)

#### YouTube-Video on "Anker Solix - Home Assistant Integration & Energiedashboard ⚡" (🇩🇪)

[![Anker Solix - Home Assistant Integration & Energiedashboard](https://img.youtube.com/vi/i-ES4cgn3qk/mqdefault.jpg)](https://www.youtube.com/watch?v=i-ES4cgn3qk)

Spoiler: Zero grid export with E1600 not possible?
[It works better as originally expected with certain requirements while considering given limitations](https://github.com/thomluther/ha-anker-solix/discussions/81).

#### YouTube-Video "Anker SOLIX 2 Pro mit Home Assistant maximal nutzen" (🇩🇪)

[![Anker SOLIX 2 Pro mit Home Assistant maximal nutzen](https://img.youtube.com/vi/XXN2ho367ZE/mqdefault.jpg)](https://www.youtube.com/watch?v=XXN2ho367ZE)

Spoiler: This shows integration capabilities before Solarbank 2 was supported with version 2.0.1

#### YouTube-Video "Anker Solix Solarbank 2 Pro: Alle Kritikpunkte behoben!" (🇩🇪)

[![Anker Solix Solarbank 2 Pro: Alle Kritikpunkte behoben](https://img.youtube.com/vi/nKXdGELBKc8/mqdefault.jpg)](https://youtu.be/nKXdGELBKc8?t=1008)


#### YouTube-Video "6 Monate Anker SOLIX mit Home Assistant" (🇩🇪)
[![6 Monate Anker SOLIX mit Home Assistant](https://img.youtube.com/vi/_0wyATg7nnk/mqdefault.jpg)](https://www.youtube.com/watch?v=_0wyATg7nnk)

Spoiler: Alkly explains his experience with Solarbank 1 and 2, the HA integration 2.4.1 and 0 grid export. Furthermore he shows how to integrate the solarbank into the energy dashboard, based on [this discussion](https://github.com/thomluther/ha-anker-solix/discussions/16)
