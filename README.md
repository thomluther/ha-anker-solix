<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Anker MI80 Logo" title="Anker MI80" align="right" height="80" />
<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solarbank E1600" align="right" height="90" />
<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/opwTD5izbjD9DjKB/picl_A17X7_normal.png" alt="Smart Meter Logo" title="Anker Smart Meter" align="right" height="80" />
<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png" alt="Solarbank 2 E1600 Logo" title="Anker Solarbank 2 E1600" align="right" height="90" />

# Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![Contributors][contributors-shield]][contributors]
[![Issues][issues-shield]][issues]
[![Discussions][discussions-shield]][discussions]
[![Community Forum][forum-shield]][forum]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![License][license-shield]](LICENSE)
![python badge][python-shield]


This Home Assistant custom component integration utilizes the [anker-solix Python library][anker-solix-api], allowing seamless integration with Anker Solix devices via the Anker cloud. It was specifically developed to monitor the Anker Solarbank E1600. Support for further Anker devices like solar micro-inverters (MI80), Solarbank 2 E1600 and the Anker smart meter has been added to the Api library and is available through the integration. The Anker power cloud also supports portable power stations (PPS) or home power panels, which may be added in the future once Api data structures for those devices are known.


## Disclaimer:

🚨 **This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the Solarbank E1600 into their smart home. Initially, the Api library as well as the integration has been developed for monitoring of the Anker Solarbank only. Meanwhile also Anker inverters can be monitored and additional enhancements allow modifications to their device settings. Any trademarks or product names mentioned are the property of their respective owners.** 🚨


## Usage terms and conditions:

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api that is also used by the official Anker mobile app. The Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore, the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

🚨 **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


## Anker Account Information

Because of the way the Anker cloud Api works, one account with e-mail/password cannot be used for the Anker mobile app and the cloud Api in parallel. The Anker cloud allows only one user request token per account at any time for security reasons. Each new authentication request by a client will create a new token and drop a previous token on the server. Therefore, usage of this integration with your mobile app account will kick out your login in the mobile App. However, starting with Anker mobile app release 2.0, you can share your defined power system(s) with 'family members'. It is recommended to create a second Anker account with a different e-mail address and share your defined power system(s) with the second account.

**Attention:**

System members cannot manage any devices of the shared system or view any of their details. You can only see the system overview in the app. Likewise it is the same behavior when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

Since the initial version of this integration did not support many setting capabilities, it was advised to use a shared account for the integration to monitor your power device values and integrate them into your home energy dashboards. The system owner account could be used in the Anker mobile app to maintain full control capabilities of your devices.
Starting with version 1.1.0, the integration supports most of the relevant parameter changes for your system and your solarbank, including modifications of the solarbank schedule. To utilize those capabilities, you must use an owner account in the integration. Likewise you could use the shared account in the Anker mobile app.

For detailed usage instructions, please refer to the [INFO](INFO.md)


## Limitations

- The used Api library is by no means an official Api and is very limited as there is no documentation at all
- The Api or the login can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in the underlying Api library
- The Api library was validated against both Anker cloud servers (EU and COM). Assignment of countries to either of the two servers however is unknown and depending on the selected country for your account, the Api login may fail or show no valid devices or sensors in the integration
- The integration sensors and entities being provided depend on whether an Anker owner account or member account is used with the integration
- The Anker account used in the integration cannot longer be used in the Anker mobile app since the cloud Api only allows 1 active client user token at a time. Existing user tokens will be removed from the server upon new client authentication requests. That means the integration kicks out the App user and vice versa.
- It was observed that solarbank or inverter devices may loose Wifi connection from time to time and will not be able to send data to the cloud. While Wifi is disconnected, the reported data may be stale. You can use the Cloud state sensor of the end device to verify the cloud connection state and potentially stale data.
- The integration supports only power devices which are defined in a power system. While it may present also standalone devices that are not defined in a system, those standalone devices do not provide any usage or consumption data via the cloud Api and therefore will not present any power entitles.
- Further devices which can be added to a power system and managed by the Anker Power cloud may be added in future if example Api response data can be provided to the developers.

**Note:**

To export randomized example data of your Anker power system configuration, please refer to the [anker-solix Python library][anker-solix-api] and the tool [export_system.py](https://github.com/thomluther/anker-solix-api#export_systempy). You can open an [issue](https://github.com/thomluther/anker-solix-api/issues) there and upload a zip file with the exported json files, together with a short description of your setup. Make sure to add your device to a Power System via the Anker mobile app before exporting the configuration. Standalone devices will barely provide data through the cloud Api.


## Supported sensors and devices

**This integration will set up the following platforms and provides support for following devices:**

Platform | Description
-- | --
`sensor` | Show info from Anker Solix Api.
`binary_sensor` | Show info from Anker Solix Api.
`switch` | Modify device settings via Anker Solix Api, temporary disable Api communication to allow parallel account usage in App
`select` | Select setting from available options
`button` | Trigger Device details refresh on demand
`number` | Change values for certain entities
`service` | Schedule services that can be applied to solarbank output preset entity

Device type | Description
-- | --
`system` | Anker Solix 'Power System' as defined in the Anker App
`solarbank` | Anker Solix Solarbank configured in the system:<br>- A17C0: Solarbank E1600 (Gen 1)<br>- A17C1: Solarbank 2 E1600 Pro<br>- A17C3: Solarbank 2 E1600 Plus<br>- A17C2: Solarbank 2 E1600 (may be supported once released)
`inverter` | Anker Solix inverter configured in the system:<br>- A5140: MI60 Inverter (out of service)<br>- A5143: MI80 Inverter
`smartmeter` | Anker Solix smart meter configured in the system:<br>- A17X7: 3 Phase Wifi Smart Meter
`smartplugs` | Anker Solix smart plugs configured in the system:<br>- A17X8: Smart Plug 2500 W (Not supported yet)

**Special note for Solarbank 2 devices and Smart Meters:**

Anker changed the data transfer mechanism to the Api cloud with Solarbank 2 power systems. While Solarbank 1 power systems transferred their power values every 60 seconds to the cloud, Solarbank 2 seems to use different intervals for Api cloud updates, which may result in **invalid data responses and unavailable entities**. Please see the [configuration option considerations for Solarbank 2 devices and Smart Meters](INFO.md#option-considerations-for-solarbank-2-devices-and-smart-meters) in the [INFO](INFO.md) for more details and how you can avoid unavailable entities.

**Other devices are neither supported nor tested with the Api library or the HA integration.**

To get additional Anker power devices added, please review the [anker-solix Python library][anker-solix-api] and contribute to [open issues](https://github.com/thomluther/anker-solix-api/issues) or Api exploration, since most devices can neither be tested by the developer, nor can they be added to the HA integration before their Api usage, parameters, structures  and fields are fully understood, interpreted and implemented into the Api library.

**Attention:**

While the integration may show standalone devices that you can manage with your Anker account, the cloud Api used by the integration does **NOT** contain or receive power values or much other details from standalone devices which are not defined to a Power System. The realtime data that you see in the mobile App under device details are either provided through the local Bluetooth interface or through an MQTT cloud server, where all your devices report their actual values but only for the time they are prompted in the App. Therefore the integration cannot be enhanced for more detailed entities of stand alone devices.


## Installation via HACS (recommended)
Use this button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.][hacs-repo-badge]][hacs-install]

Or following procedure:
1. Open the [HACS](https://hacs.xyz) panel in your Home Assistant frontend.
1. Navigate to the "Integrations" tab.
1. Click the three dots in the top-right corner and select "Custom Repositories."
1. Add a new custom repository:
   - **URL:** `https://github.com/thomluther/hacs-anker-solix`
   - **Category:** Integration
1. Click "Save" and then click "Install" on the `Anker Solix` integration.

Unfortunately, HACS does not automatically install the optional entity images that must be located within the web accessible `www` folder, which is located in your HA installation configuration folder. Please see [Optional entity pictures](#optional-entity-pictures) for instructions to copy the image files manually.

**Installation Notes:**
- It was observed that when adding the repository to HACS, an error may occur although it was added. You may check if you can find Anker Solix listed as possible HACS integration to be installed. If not, try to add the repository again.
- After adding the custom repository and installing the integration under HACS, you must restart Home Assistant to pick up the changes in your custom integration folder
   - HA 2024.02 will report the required restart automatically under problems
- After HA restart, you can install and configure the integration like a normal core integration via the HA UI:
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


## Integration configuration is done in the UI

For detailed instructions on how to configure and use the integration, please refer to [INFO](INFO.md).

Note: When you make changes to the integration folder content, you need to restart Home Assistant to pick up those changes
for the container or virtual environment where Home Assistant is being started. This is applicable as well when the integration is updated manually or via HACS.
<!---->


## Issues, Q&A and other discussions

If you have a problem, [review existing issues or open a new issue](https://github.com/thomluther/hacs-anker-solix/issues) with detailed instructions describing the problem. You may need to enable Debug Output for your Integration configuration. Review your debug output before you post it. While sensitive login information is masked, your unique device information as returned from the Api is not masked (serial numbers, IDs etc). You may want to change that globally before providing a debug output.

If you have questions, observations, advises or want to share your experience, feel free to open a new [discussion topic](https://github.com/thomluther/hacs-anker-solix/discussions).


## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md).
As a starter, you may want to add more [translations](https://github.com/thomluther/hacs-anker-solix/discussions/12) for your native language.


## Attribution

- [anker-solix-api library][anker-solix-api]
- [solix2mqtt project](https://github.com/tomquist/solix2mqtt)
- [Solaredge HA core integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/solaredge)
- [ha-hoymiles-wifi custom integration](https://github.com/suaveolent/ha-hoymiles-wifi)


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/hacs-anker-solix
[anker-solix-api]: https://github.com/thomluther/anker-solix-api
[releases]: https://github.com/thomluther/hacs-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/hacs-anker-solix.svg?style=for-the-badge
[issues]: https://github.com/thomluther/hacs-anker-solix/issues
[issues-shield]: https://img.shields.io/github/issues/thomluther/hacs-anker-solix.svg?style=for-the-badge
[discussions]: https://github.com/thomluther/hacs-anker-solix/discussions
[discussions-shield]: https://img.shields.io/github/discussions/thomluther/hacs-anker-solix.svg?style=for-the-badge
[contributors]: https://github.com/thomluther/hacs-anker-solix/contributors
[contributors-shield]: https://img.shields.io/github/contributors/thomluther/hacs-anker-solix.svg?style=for-the-badge
[buy-me-coffee]: https://www.buymeacoffee.com/thomasluthe
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-install]: https://my.home-assistant.io/redirect/hacs_repository/?owner=thomluther&repository=https%3A%2F%2Fgithub.com%2Fthomluther%2Fhacs-anker-solix&category=Integration
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/hacs-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange

## Additional Resources

- [Usage instructions and configuration of the integration](INFO.md)
- [Possibilities to integrate the Solarbank into your Energy Dashboard](https://github.com/thomluther/hacs-anker-solix/discussions/16)
- [Surplus charge automation for Solarbank E1600 (1st generation)](https://github.com/thomluther/hacs-anker-solix/discussions/81)

If you need more assistance on the topic, please have a look at the following external resources:

### Blog-Posts
- [simon42 - Anker Solix – Home Assistant Energiedashboard & Steuerung](https://www.simon42.com/anker-solix-home-assistant/)

### Videos
#### YouTube-Video "Anker SOLIX in Home Assistant integrieren" (🇩🇪)
[![Anker SOLIX in Home Assistant integrieren](https://img.youtube.com/vi/66jbUnKnkSA/mqdefault.jpg)](https://www.youtube.com/watch?v=66jbUnKnkSA)

#### YouTube-Video on "Anker Solix - Home Assistant Integration & Energiedashboard ⚡" (🇩🇪)
[![Anker Solix - Home Assistant Integration & Energiedashboard](https://img.youtube.com/vi/i-ES4cgn3qk/mqdefault.jpg)](https://www.youtube.com/watch?v=i-ES4cgn3qk)

Spoiler: Zero grid export with E1600 not possible?
[It works better as originally expected with certain requirements and given limitations](https://github.com/thomluther/hacs-anker-solix/discussions/81).

#### YouTube-Video "Anker SOLIX 2 Pro mit Home Assistant maximal nutzen" (🇩🇪)
[![Anker SOLIX 2 Pro mit Home Assistant maximal nutzen](https://img.youtube.com/vi/XXN2ho367ZE/mqdefault.jpg)](https://www.youtube.com/watch?v=XXN2ho367ZE)

Spoiler: This shows integration capabilities before Solarbank 2 was supported with version 2.0.1
