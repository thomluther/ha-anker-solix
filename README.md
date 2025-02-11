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


This Home Assistant custom integration utilizes the [anker-solix Python library][anker-solix-api], allowing seamless integration with Anker Solix devices via the Anker power cloud. It was specifically developed to monitor the Anker Solarbank E1600. Support for further Anker devices like solar micro-inverters (MI80), Solarbank 2 E1600 and the Anker smart meter has been added to the Api library and is available through the integration. The Anker power cloud also supports portable power stations (PPS), home Power Panels or home energy systems (HES) which are not or only partially supported by the api library. They may be added in the future once Api data structures for those devices are known and regular consumption data will be sent to the Anker Power cloud.

**Notes:**

Anker power devices which are not configured into a power system in your Anker mobile app typically do **NOT** provide any consumption data to the Anker power cloud. Likewise it has turned out, that portable power stations (PPS), power banks or power cooler do not send data to the Anker power cloud either since they are not configurable as a main power system device.Therefore, the Api library cannot get consumption data of standalone devices.

Please refer to [supported sensors and devices](#supported-sensors-and-devices) for a list of supported Anker Solix devices.

## Disclaimer:

🚨 **This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the devices of Anker Solix power systems into their smart home. Any trademarks or product names mentioned are the property of their respective owners.** 🚨


## Usage terms and conditions:

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api that is also used by the official Anker mobile app. The Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore, the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

🚨 **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


# Table of contents

1. **[Disclaimer](#disclaimer)**
1. **[Usage terms and conditions](#usage-terms-and-conditions)**
1. **[Anker Account Information](#anker-account-information)**
1. **[Limitations](#limitations)**
1. **[Supported sensors and devices](#supported-sensors-and-devices)**
1. **[Special device notes](#special-device-notes)**
   * [Solarbank 2 devices and Smart Meters](#solarbank-2-devices-and-smart-meters)
   * [Solarbank 2 AC devices](#solarbank-2-ac-devices)
   * [Combined Solarbank 2 systems containing cascaded Solarbank 1 devices](#combined-solarbank-2-systems-containing-cascaded-solarbank-1-devices)
   * [Power Panels](#power-panels)
   * [Other devices](#other-devices)
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

Because of the way the Anker cloud Api works, one account with e-mail/password cannot be used for the Anker mobile app and the cloud Api in parallel. The Anker cloud allows only one user request token per account at any time for security reasons. Each new authentication request by a client will create a new token and drop a previous token on the server. Therefore, usage of this integration with your mobile app account will kick out your login in the mobile App. However, starting with Anker mobile app release 2.0, you can share your defined power system(s) with 'family members'. It is recommended to create a second Anker account with a different e-mail address and share your defined power system(s) with the second account.

**Attention:**

System members cannot manage any devices of the shared system or view any device details. You can only see the system overview in the app. Likewise you have the same behavior when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

Since the initial version of this integration did not support many setting capabilities, it was advised to use a shared account for the HA integration to monitor your power system values and integrate them into your home energy dashboards. The system owner account could be used in the Anker mobile app to maintain full control capabilities of your devices.
Starting with version 1.1.0, the integration supports most of the relevant parameter changes for your system and your solarbank, including modifications of the solarbank schedule. To utilize those capabilities, you must use an owner account in the HA integration. Likewise you can use the shared account in the Anker mobile app for system home page monitoring.

For detailed usage instructions, please refer to the [INFO](INFO.md)


## Limitations

- The used Api library is by no means an official Api and is very limited as there is no documentation at all
- The Api library or the login can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in the underlying Api library
- The Api library was validated against both Anker cloud servers (EU and COM). Assignment of countries to either of the two servers however is unknown and depending on the selected country for your account. Upon wrong server assignment for your registered country, the Api may login but show no valid systems, devices or sensors in the integration
- The integration sensors and entities being provided depend on whether an Anker owner account or member account is used with the integration
- The Anker account used in the integration cannot longer be used in the Anker mobile app since the cloud Api allows only 1 active client user token at a time. Existing user tokens will be removed from the server upon new client authentication requests. That means the integration kicks out the App user and vice versa. The behavior is the same as using the Anker app on multiple devices, which will kick out each other.
- It was observed that solarbank or inverter devices may loose Wifi connection from time to time and will not be able to send data to the cloud. While device Wifi is disconnected, the reported data in the cloud may be stale. You can use the cloud state sensor of the end device to verify the device cloud connection state and recognize potentially stale data.
- The integration can support only Solix power devices which are defined in a power system via the Anker mobile app. While it may present also standalone devices that are not defined in a system, those standalone devices do not provide any usage or consumption data via the cloud Api and therefore will not present any power entities.
- Further devices which can be added to a power system and managed by the Anker Power cloud may be added in future once examples of Api response data can be provided to the developers.

**Note:**

To export randomized example data of your Anker power system configuration, please refer to the [anker-solix Python library][anker-solix-api] and the tool [export_system.py](https://github.com/thomluther/anker-solix-api#export_systempy). A new [HA service/action to export anonymized Api response data](INFO.md#export-systems-action) was added to the integration to simplify data collection in a downloadable zip file.
You can open a new [issue](https://github.com/thomluther/anker-solix-api/issues) in the api library repo and upload the zip file with the exported json files, together with a short description of your setup. Make sure to add your device to a Power System via the Anker mobile app before exporting the configuration. Standalone devices will barely provide data through the cloud Api.


## Supported sensors and devices

This integration will set up the following HA platforms and provides support for following Anker Solix devices:

Platform | Description
-- | --
`sensor` | Show info from Anker Solix Api.
`binary_sensor` | Show info from Anker Solix Api.
`switch` | Modify device settings via Anker Solix Api, temporary disable Api communication to allow parallel account usage in App
`select` | Select settings from available options
`button` | Trigger device details refresh on demand
`number` | Change values for certain entities
`datetime` | Change date and time for certain entities
`service` | Various Solarbank schedule or Api related services/actions

Device type | Description
-- | --
`account` | Anker Solix user account used for the configured hub entry. It collects all common entities belonging to the account or api connection.
`system` | Anker Solix 'Power System' as defined in the Anker app. It collects all entities belonging to the defined system.
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1)<br>- A17C1: Solarbank 2 E1600 Pro<br>- A17C3: Solarbank 2 E1600 Plus<br>- A17C2: Solarbank 2 E1600 AC (initial support)
`inverter` | Anker Solix inverter configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Smart meter configured in the system:<br>- A17X7: Anker 3 Phase Wifi Smart Meter<br>- SHEM3: Shelly 3EM Smart Meter<br>- SHEMP3: Shelly 3EM Pro Smart Meter
`smartplug` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W (No individual device setting supported yet)
`powerpanel` | Anker Solix Power Panels configured in the system:<br>- A17B1: SOLIX Home Power Panel for SOLIX F3800 power stations (Non EU market)


## Special device notes

### Solarbank 2 devices and Smart Meters

Anker changed the data transfer mechanism to the Api cloud with Solarbank 2 power systems. While Solarbank 1 power systems transfer their power values every 60 seconds to the cloud, Solarbank 2 seems to use different intervals for their data updates in the cloud, which may result in **invalid data responses and unavailable entities**. Please see the [configuration option considerations for Solarbank 2 systems](INFO.md#option-considerations-for-solarbank-2-systems) in the [INFO](INFO.md) for more details and how you can avoid unavailable entities.


### Solarbank 2 AC devices

The Solarbank 2 AC model comes with new features and initial support has been implemented with version 2.5.0. While all provided usage modes and options can be toggled with a single entity, the Integration does not support yet any modification of the new Use Time plan, since this is a new and complex plan format that requires additional work and testing.

Note:

There may be issues when toggling the usage modes or output preset in the manual usage mode since not all changes may be applied by the device. This still has to be investigated and validated by YOU, the AC device owner. Api testing and exploration may be required via the Api library. See issue [#198](https://github.com/thomluther/ha-anker-solix/issues/198).


### Combined Solarbank 2 systems containing cascaded Solarbank 1 devices

This coupling feature for 1st generation Solarbank devices was [announced in May 2024](https://www.ankersolix.com/de/blogs/balkonkraftwerk-mit-speicher/solarbank-der-ersten-generation-und-solarbank-2-pro-zusammen-fur-mehr-energiekontrolle) and [delivered in Dec 2024](https://www.ankersolix.com/de/blogs/balkonkraftwerk/die-1-generation-der-solarbank-vereint-sich-mit-dem-energiesystem-der-solarbank-2-pro-plus).
It turns out that Anker implemented just the bare minimum to support such combined systems. As users noticed, the power totals and energy statistics for such systems reflect ONLY the SB2 data, but not any SB1 data. That means you don't see anymore the SB1 solar power / energy during the day, but the SB1 discharge at night counts as solar power/energy of the SB2 during the night. All reported charge or discharge data does not reflect anything of the SB1 devices in the system. So the SB1 is pretty much a black box for the Anker home page, which is the page that can be accessed by system members.
Furthermore the SB1 device(s) may have different schedules in combined systems. While SB2 is running in an automatic mode, the SB1 has its own schedule with all known controls for any number of time intervals. When SB2 is switched to manual mode however, it enforces another, minimalistic single interval schedule to the SB1 devices which is not accessible via the mobile App. This schedule has no interval control elements. The output preset is the only value for a whole day interval and is determined by the SB2, depending on its manual plan settings and SOC. When adding a SB1 device into a SB2 system, the Solarbank 2 will get configured as inverter type for the cascaded SB1 device. Therefore the output preset in this minimalistic schedule can also be 0 W for SB1, without any 0 W output switch installed. To prevent any SB1 schedule modifications while the enforced schedule is active, the integration will make all affected control entities unavailable to prevent user changes. Therefore you may see unavailable controls in cascaded SB1 devices that cannot be modified any longer, otherwise this may screw up the presented values and schedule settings, which would always be applied to the real SB1 schedule, even if inactive.
To present correct total values for the combined system, the Api library corrects also the totals in the Api response based on proper accumulation of individual device values:
  - Total solar power: SB1 device(s) solar power + SB2 device solar power - SB1 device(s) output power
  - Total output power: Remains SB2 device output power
  - Total SOC: Weighted average SOC across all devices, considering also number of SB2 battery packs
  - Total battery power:
    - The device battery power has always been calculated by the library, since the Api never reflected reliable charge or discharge power fields
    - It is calculated as Solar power - Output power, resulting in the overall battery power for the device (positive charge power and negative discharge)
    - Since a single device cannot charge and discharge at the same point in time, the device battery power typically reflects the complete charge OR discharge power
    - The total battery power simply accumulates each device's battery power, and thus reflecting the total NET battery power
    - However, this total NET battery power of multiple devices cannot reflect the total charge or discharge power at any given time, since a SB1 discharge of 100 W and a charge of those 100 W by the SB2 will result in 0 W NET battery power. So neither the 100 W charge power nor the 100 W discharge power are reflected in the total (NET) battery power value.

**Important:**

If you derived your HA energy integral sensors or other helpers from a positive/negative value split of the system battery power, your charge and discharge energy calculations will not be accurate anymore in combined systems. To achieve a correct charge and discharge energy calculation for your energy dashboard, you need to separate the charge and discharge power individually from each device battery power value. Then you can accumulate correct energies in following 2 ways:
  - Accumulate charge and discharge energy individually for each device and add them all to the energy dashboard. This allows granular energy tracking per Solarbank, since the dashboard will automatically accumulate energies of same type, but display each in a different color. This is the recommended option.
  - Create total charge and discharge power helper entities, that summarize the device power values separately. Then you can accumulate the total charge and discharge energies from those new summary helper entities.


### Power Panels:

Power Panels are not supported in the EU market, therefore the EU cloud api server currently does not support either the required endpoints. Furthermore it was discovered that the F3800 power stations attached to the Power Panel are not tracked as system devices. Actual power consumption data in the cloud api was not discovered yet and it is assumed that the power panel home page consumption values are merged by the App from the MQTT cloud server only if the App home page is viewed. A work around for monitoring some power values and overall SOC has been implemented by extracting the last valid 5 minute average data that is collected with the system energy statistics (Basically the last data point that is visible in the various daily diagrams of your mobile app). Power Panel owners need to explore and document cloud Api capabilities to further expand any Power Panel system or device support. Please refer to issue [Add F3800/BP3800 Equipment when connected to Home Power Panel](https://github.com/thomluther/anker-solix-api/issues/117) for contribution.

### Other devices

Other devices not listed in the support table are neither supported nor tested with the Api library or the HA integration. Be aware that devices are only supported by the Anker cloud Api if they can be added into a Power System. Stand alone devices such as portable power stations (PPS), power charger or power cooler, cannot be added to a system and therefore do not provide any data into the power cloud.

To get additional Anker power devices/systems added, please review the [anker-solix Python library][anker-solix-api] and contribute to [open issues](https://github.com/thomluther/anker-solix-api/issues) or Api exploration. Most devices can neither be tested by the developer, nor can they be added to the HA integration before their Api usage, parameters, structures and fields are fully understood, interpreted and implemented into the Api library.

**Attention:**

While the integration may show standalone devices that you can manage with your Anker account, the cloud Api used by the integration does **NOT** contain or receive power values or much other details from standalone devices which are not defined to a Power System. The realtime data that you see in the mobile app under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their actual values but only for the time they are prompted in the App. Therefore the integration cannot be enhanced for more detailed entities of stand alone devices.


## Installation via HACS (recommended)

Use this button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-install]

Or following procedure for HACS 2.0 or later:
1. Open the [HACS](https://hacs.xyz) panel in your Home Assistant frontend.
1. Click the three dots in the top-right corner and select "Custom Repositories."
1. Add a new custom repository via the Popup dialog:
   - **Repository URL:** `https://github.com/thomluther/ha-anker-solix`
   - **Type:** Integration
1. Click "Add" and verify that the `Anker Solix` repository was added to the list.
1. Close the Popup dialog and verify that `Anker Solix` integration is now listed in the Home Assistant Community Store.
1. Install the integration

Unfortunately, HACS does not automatically install the optional entity images that must be located within the web accessible `www` folder, which is located in your HA installation configuration folder. Please see [Optional entity pictures](#optional-entity-pictures) for instructions to copy the image files manually.

### Installation Notes
- It was observed that when adding the repository to HACS via the button, an error may occur although it was added. You may check if you can find Anker Solix listed as possible HACS integration to be installed. If not, try to add the repository again.
- After adding the custom repository and installing the integration under HACS, you must restart Home Assistant to pick up the changes in your custom integration folder
   - HA 2024.02 will report the required restart automatically under problems
- After HA restart, you can install and configure the integration like a normal core integration via the HA frontend:
   - Go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix". It should now be listed as community integration


## Manual Installation

1. Using the tool of choice to open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `anker_solix`.
1. Download _all_ the files from the `custom_components/anker_solix/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix"


## Optional entity pictures

If you want to use the optional entity pictures that are shown in the example screenshots in the [INFO](INFO.md), you need to copy the `images` folder from the integration installation path to the `www` folder of your Home Assistant installation configuration folder. If you operate a Home Assistant OS device, you can preferably use file management Add Ons such as Studio Code Server or File Explorer to copy this folder after the installation:
1. Navigate to the `CONFIG` folder of your HA installation (where your configuration.yaml is located)
1. Navigate to `custom_components/anker_solix/` folder and copy the `images` subfolder containing the entity pictures
1. Go back to your `CONFIG` folder and navigate to or create the `www/community/anker_solix` folder structure if not existing
1. Paste the `images` folder into the created `anker_solix` community subfolder

 Once the images are available in `www/community/anker_solix/images/`, they will be picked up when the integration is (re-)creating the entities, like on first creation or re-load of the configuration entry.
 Make sure to reload your HA UI browser window without cache to get the entity pictures displayed correctly.


## Integration configuration and usage

For detailed instructions on how to configure and use the integration, please refer to [INFO](INFO.md).

Note: When you make changes to the integration folder content, you need to restart Home Assistant to pick up those changes for the container or virtual environment where Home Assistant is being started. This is applicable as well when the integration is updated manually or via HACS.


## Issues, Q&A and other discussions

If you have a problem, [review existing issues or open a new issue](https://github.com/thomluther/ha-anker-solix/issues) with detailed instructions describing the problem. You may need to enable Debug Output for your Integration configuration. Review your debug output before you post it. While sensitive login information is masked, your unique device information as returned from the Api is not masked (serial numbers, IDs etc). You may want to change that globally before providing a debug output.

If you have questions, observations, advises or want to share your experience, feel free to open a new [discussion topic](https://github.com/thomluther/ha-anker-solix/discussions).


## Contributions are welcome!

If you want to contribute to this project, please read the [Contribution guidelines](CONTRIBUTING.md).
As a starter, you may want to add more [translations](https://github.com/thomluther/ha-anker-solix/discussions/12) for your native language.


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

[def]: #issues-