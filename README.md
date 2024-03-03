<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="90" />
<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="90" />

# Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Contributors][contributors-shield]][contributors]
[![Downloads][downloads-shield]][downloads]
[![Discussions][discussions-shield]][discussions]
[![Community Forum][forum-shield]][forum]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

[![License][license-shield]](LICENSE)
![python badge][python-shield]


This Home Assistant custom component integration utilizes the [anker-solix Python library][anker-solix-api], allowing seamless integration with Anker Solix devices via the Anker cloud. It was specifically developped to monitor the Anker Solarbank E1600. Support for further Anker devices like solar micro-inverters (MI80) have been add to the Api library and are available through the integration. The Anker Power cloud also supports portable power stations (PPS) or home Power Panels which may be added in future once Api data structures for those devices is known.


# 🚨 Work in progress, this is not released yet 🚨


## Disclaimer:

**This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the Solarbank E1600 into their smart home. Initially the Api library as well as the integration have been developped for monitoring of the Anker Solarbank only. Meanwhile also Anker inverters can be monitored and future enhancements may allow also modifications to their device settings. Any trademarks or product names mentioned are the property of their respective owners.**


## Usage terms and conditions:

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api that is also used by the official Anker mobile app. The Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

**The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.**


## Anker Account Information

Because of the way the Anker cloud Api works, one account with e-mail/password cannot be used for the Anker mobile app and the cloud Api in parallel. The Anker cloud allows only one user request token per account at any time for security reasons. Each new authentication request by a client will create a new token and drop a previous token on the server. Therefore usage of this integration with your mobile app account will kick out your login in the mobile App. However, starting with Anker mobile app release 2.0, you can share your defined power system(s) with 'family members'. Therefore it is recommended to create a second Anker account with a different e-mail address and share your defined power system(s) with the second account.

**Attention:**

System members cannot manage (yet) any devices of the shared system or view any of their details. You can only see the system overview in the app. Likewise it is the same behavior when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

Since the current version of this integration does not support many setting capabilities, it is advised to use a shared account for the integration to monitor your power device values and integrate them into your home energy dashboards. The system owner account should be used in the Anker mobile app to maintain full control capabilities of your devices.

For detailed usage instructions, please refer to the [INFO](INFO.md)


## Limitations

- The used Api library is by no means an official Api and is very limited as there is no documentation at all
- The Api or the login can break at any time, or Api requests can be removed/added/changed and break some of the endpoint methods used in the underlying Api library
- The Api library is currently only validated against the EU Anker cloud server. Assignment of countries to the other common cloud server is unknown and depending on the selected country for your account, the Api login may fail or show no valid devices or sensors in the integration
- The integration sensors and entities being provided depend on whether an Anker owner account or member account is used with the integration
- The Anker account used in the integration cannot longer be used in the Anker mobile app since the cloud Api only allows 1 active client user token at a time. Existing user tokens will be removed from the server upon new client authentication requests. That means the integration kicks out the App user and vice versa.
- The initial integration release supports only Solarbank and Anker inverter devices. Further devices managed by the Anker Power cloud may be added in future if example Api response data can be provided to the developpers (open issue on git with example data)
- The initial integration release supports only following settings when using a system owner account:
   - Auto-Update setting of Solarbank device


## Supported sensors and devices

**This integration will set up the following platforms and provides support for following devices:**

Platform | Description
-- | --
`sensor` | Show info from Anker Solix Api.
`binary_sensor` | Show info from Anker Solix Api.
`switch` | Modify device settings via Anker Solix Api, temporary disable Api communication to allow parallel account usage in App
`button` | Trigger Device details refresh on demand

Device type | Description
-- | --
`system` | Anker Solix 'Power System' as defined in the Anker App
`solarbank` | Anker Solix Solarbanks configured in the system
`inverter` | Anker Solix inverters configured in the system


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

Unfortunately, HACS does not automatically install the optional entity images that must be located within the web accessible www folder, that is located in your installation configuration folder. For instructions to copy the image files manually, see below.


## Manual Installation

1. Using the tool of choice to open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `anker_solix`.
1. Download _all_ the files from the `custom_components/anker_solix/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix"


## Optional entity pictures
If you want to use the optional entity pictures that are shown in the example screenshots in the [INFO](INFO.md), you need to copy the `images` folder from the integration installation path to the `www` folder of your Home Assistant installation. If you operate a Home Assistant OS device, you can preferrably use file management Add Ons such as Studio Code Server or File Explorer to copy this folder after the installation:
1. Navigate to the `CONFIG` folder of your HA installation
1. Navigate to `customer_componets/anker_solix/` folder and copy the `images` subfolder containing the integration pictures
1. Back in `CONFIG` folder, navigate to the `www\community\anker_solix` folder or create the folder structure if not existing
1. Paste the `images` folder into the created `anker_solix` community subfolder

 Once the images are available, they will be picked up when the integration is (re)-creating the entities, like on first creation or re-load of the configuration entry.


## Integration configuration is done in the UI

Note: When you make changes to the integration folder content, you need to restart Home Assistant to pick up those changes
for the container or virtual environment where Home Assistant is being started. This is applicable as well when the integration is updated manually or via HACS.
<!---->


## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)


## Attribution

- [anker-solix-api library][anker-solix-api]
- [Solaredge HA core integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/solaredge)
- [ha-hoymiles-wifi custom integration](https://github.com/suaveolent/ha-hoymiles-wifi)
- [solix2mqtt project](https://github.com/tomquist/solix2mqtt)


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/hacs-anker-solix
[anker-solix-api]: https://github.com/thomluther/anker-solix-api
[commits]: https://github.com/thomluther/hacs-anker-solix/commits
[commits-shield]: https://img.shields.io/github/commits/thomluther/hacs-anker-solix.svg?style=for-the-badge
[releases]: https://github.com/thomluther/hacs-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/hacs-anker-solix.svg?style=for-the-badge
[discussions]: https://github.com/thomluther/hacs-anker-solix/discussions
[discussions-shield]: https://img.shields.io/github/discussion/thomluther/hacs-anker-solix.svg?style=for-the-badge
[contributors]: https://github.com/thomluther/hacs-anker-solix/contributors
[contributors-shield]: https://img.shields.io/github/contributors/thomluther/hacs-anker-solix.svg?style=for-the-badge
[downloads]: https://github.com/thomluther/hacs-anker-solix/downloads
[downloads-shield]: https://img.shields.io/github/downloads/thomluther/hacs-anker-solix.svg?style=for-the-badge
[buy-me-coffee]: https://www.buymeacoffee.com/thomasluthe
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-install]: https://my.home-assistant.io/redirect/hacs_repository/?owner=thomluther&repository=https%3A%2F%2Fgithub.com%2Fthomluther%2Fhacs-anker-solix&category=Integration
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/hacs-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange

