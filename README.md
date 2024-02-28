<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="100" />

# Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Community Forum][forum-shield]][forum]
[![License][license-shield]](LICENSE)
![python badge][python-shield]

This Home Assistant custom component utilizes the [anker-solix](anker-solix) Python library, allowing seamless integration with Anker Solix devices via the cloud. It was specifically developped to monitor the Anker Solarbank E1600. Further Anker devices like solar micro-inverters or power stations may be added in future once Api data structures for those devices is known.

### Disclaimer:
**This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools for interacting with the Solarbank E1600,  initially for monitoring only. Any trademarks or product names mentioned are the property of their respective owners.**

## Anker Account Information

Because of the way the Anker Solix Api works, one account with email/password cannot be used for the Anker mobile App and the cloud Api in parallel.
The Anker cloud allows only one user request token per account at any time. Each new authentication request by a client will create a new token and drop a previous token.
Therefore usage of this integration will kick out your account login in the mobile App.
However, starting with Anker mobile App release 2.0, you can share your defined system(s) with 'family members'.
Therefore it is recommended to create a second Anker account with a different email address and share your defined system(s) with the second account.

Attention: A shared account is only a member of the shared system, and as such currently has no permissions to access or query device details of the shared system,
neither in the mobile App nor in the cloud Api. Therefore some device setting sensors may not show up if the configured user has no permissions to query shared device details.
Anyway, since the integration allows only monitoring capabilities in its initial release, it is advised to use a shared account for the integration and the system owner
account in the Anker mobile App to maintain control capabilities of your devices.

## Limitations

- The used Api library is by no means an official Api and is very limited as there is no documentation at all.
- The Api or the login can break at any time, or Api request can be removed/added/changed and break some of the endpoint methods used in this Api library.
- The Api is currently only validated against the EU Anker cloud. Assignment of countries is unknown and depending on the selected Country (code), Api usage may fail.
- The information that can be queried and the sensors being provided depend on whether an Anker system owner account or a member account is used with the integration.
- The Anker account that is used in the integration cannot longer be used in the Anker mobile App since the cloud Api only allows 1 active client user token at a time.
- Existing user tokens will be removed from the server upon new client authentication request. That means the integration kicks out the App user and vice versa.

## Supported sensors and devices

**This integration will set up the following platforms and provides support for following devices:**

Platform | Description
-- | --
`sensor` | Show info from Anker Solix Api.

Device type | Description
-- | --
`solarbank` | Anker Solix E1600 Solarbank


## Installation via HACS (recommended)
1. Open the [HACS](https://hacs.xyz) panel in your Home Assistant frontend.
1. Navigate to the "Integrations" tab.
1. Click the three dots in the top-right corner and select "Custom Repositories."
1. Add a new custom repository:
   - **URL:** `https://github.com/thomluther/hacs-anker-solix`
   - **Category:** Integration
1. Click "Save" and then click "Install" on the `Anker Solix` integration.


## Manual Installation

1. Using the tool of choice to open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `anker_solix`.
1. Download _all_ the files from the `custom_components/anker_solix/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anker Solix"

## Integration configuration is done in the UI

Note: When you make changes to the integration folder content, you need to restart Home Assistant to pick up those changes
for the container or virtual environment where Home Assistant is being started.
<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

## Attribution

- [Solaredge HA core integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/solaredge)
- [ha-hoymiles-wifi custom integration](https://github.com/suaveolent/ha-hoymiles-wifi)
- [anker-solix-api library][anker-solix]
- [solix2mqtt project](https://github.com/tomquist/solix2mqtt)

## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/thomasluthe)

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/hacs-anker-solix
[commits]: https://github.com/thomluther/hacs-anker-solix/commits
[commits-shield]: https://img.shields.io/github/commits/thomluther/hacs-anker-solix.svg?style=for-the-badge
[releases]: https://github.com/thomluther/hacs-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/hacs-anker-solix.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/hacs-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange

