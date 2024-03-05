<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="90" />
<img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solix Api" align="right" height="90" />

# How to use the Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![Discussions][discussions-shield]][discussions]

[![License][license-shield]](LICENSE)
![python badge][python-shield]


## Disclaimer:

🚨 **This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the Solarbank E1600 into their smart home. Initially the Api library as well as the integration have been developed for monitoring of the Anker Solarbank only. Meanwhile also Anker inverters can be monitored and future enhancements may allow also modifications to their device settings. Any trademarks or product names mentioned are the property of their respective owners.** 🚨


## Usage terms and conditions:

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api that is also used by the official Anker mobile app. The Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore, the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

🚨 **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


## Device structure used by the integration

This Home Assistant custom component integration allows seamless integration with Anker Solix devices via the Anker cloud.
It follows the Anker cloud Api structures, which allows registered users to define one or more Power Systems, called site in the Api with a unique site_id.
The configured user must have defined at least one owning system, or have access to a shared system, to see devices for a configured integration account.
For each accessible system by the configured account, the integration will create one System Device with the appropriate system sensors. These sensors typically reflect the values that are presented in the Anker mobile app main view of a system.
Following example shows how configured integration accounts may look:

![Configured Integration][integration-img]

For each end device the system owner has configured into a system, the integration will create an End Device entry, which is controlled by the System Device.
So far, available accessory devices such as the 0W Output switch are not manageable on its own. Therefore they are currently presented as entity of the End Device entry that is managing the accessory.

Following are anonymized examples how the Anker power devices will be presented:

**1. System Device**

![System Device][system-img]
![Connected Devices][connected-img]

**2. Solarbank Device**

![Solarbank Device][solarbank-img]

**3. Inverter Device**

![Inverter Device][inverter-img]


The integration will setup the entities with unique ids based on device serials or a combination of serials. This makes them truly unique and provides the advantage that the same entities can be re-used after switching the integration configuration to another shared account. While the entity history is not lost, it implies that you cannot configure different accounts at the same time when they share a system. Otherwise, it would cause HA setup errors because of non unique entities. Therefore, new integration configurations are validated and not allowed when they share systems or devices with an active configuration.
If you want to switch from your main account to the shared account, delete first the active configuration and then create a new configuration with the other account. When the devices and entities for the configured account will be created, deleted entities will be re-activated if their data is accessible via Api for the configured account. That means if you switch from your main account to the shared account, only a subset of entities will be re-activated. The other deleted entities and their history data may remain available until your configured recorder interval is over.


## Data refresh configuration options

The data on the cloud that can be retrieved via the Api is refreshed only once per minute. Therefore, it is recommended to leave the integration refresh interval set to the default minimum of 60 seconds, or increase it even further when no frequent updates are required. Refresh intervals are configurable from 30-600 seconds, but less than 60 seconds will not provide more actual data and just cause unnecessary Api traffic.
During each refresh interval, the power sensor values will be refreshed, along with the actual system configuration and available end devices. There are more end device details available showing their actual settings, like power cut off, auto-upgrade, schedule etc. However, those details require much more Api queries and therefore are refreshed less frequently. The device details refresh interval can be configured as a multiplier of the normal data refresh interval. With the default options of the configured account, the device details refresh will run every 10 minutes, which is typically by far sufficient. If a device details update is required on demand, each end device has a button that can be used for such a one-time refresh. However, the button will re-trigger the device details refresh only when the last refresh was more than 30 seconds ago to avoid unnecessary Api traffic.

The refresh options can be configured after creation of an integration entry. Following are the default options:

![Options][options-img]


## Anker account limitation and usage recommendations

Usage of the same Anker account in the integration and the Anker mobile app at the same time is not possible due to security reasons enforced by Anker. For more details refer to the Anker Account information in the [README](README.md).
Therfore, it is recommended to use a second account in the integration that has the power system shared as a member. For instruction to create a second account and share the system, see below.
Following is the integration configuration dialog:

![configuration][config-img]


**Attention:**

System members cannot manage (yet) any devices of the shared system or view any of their details. You can only see the system overview in the app. Likewise it is the same behaviour when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

A work around to overcome this account limitation has been implemented via an Api switch in the System Device. When disabled, the integration stops any Api communication for all systems of the disabled account. During that time, you can use the owning account again for login through the Anker app and modify device settings as needed. Afterwards you can re-activate Api communication in the integration again, which will automatically re-login and continue reporting data. While the Api switch is off, all sensors will be unavailable to avoid reporting of stale data.

To simplify usage of this workaround, please see below for an example automation, which sends a sticky mobile notification when the Api switch was disabled, using actionable buttons to launch the Anker App directly from the notification. It provides also actionable buttons to re-enable the switch again and clear the sticky notification. This avoids forgetting to re-enable your data collection when you are finished with your tasks in the Anker App.


## How to create a second Anker Power account

If you have the Anker app installed on 2 different devices, the account creation and system sharing will be a little bit easier. Following is a high-level guideline how to create a second account and share the system on a single device:
1. Go to your profile in the Anker app, click on your name at the top and then Log out.
1. Then create a new Anker power account via the app. You will need a second e-mail address. (This could also be an alias address that you set up with your e-mail provider)
1. Complete the registration process. This may have to be confirmed via a temporary code that is sent to the used e-mail address.
1. Once you are logged in with the secondary account, log out again in the app as in step 1.
1. Log in again with your main account and go to your profile.
1. The first item there is Manage System. Go into Manage System and then click on the arrow to the right of the system you want to share.
1. Then you will see Invite Members at the bottom, where you must enter the e-mail of your second account.
1. Then log out again as in step 1.
1. Log in with the second account and go to your systems via the profile.
1. There you should now see the invitation from your main account. You must confirm the invitation to activate shared system access.
1. Just now you access the system as a member. The owner will also get a confirmation that you accepted the invitation.


## Automation to send and clear sticky, actionable notifications based on Api switch setting

Following automation can be used to send a sticky actionable notification to your Android mobile when the companion app is installed. It allows you to launch the Anker app or to re-activate the Api again for your system.

![notification][notification-img]

Make sure to replace the entities used in the example below with your own entities. The system variable is automatically generated based on the device name of the entity that triggered the state change.

**Note:**
If you want to modify the notification to work with your iPhone, please refer to the [HA companion App documentation](https://companion.home-assistant.io/docs/notifications/notifications-basic/) for IOS capabilities.

```
alias: Notify - Anker Solix Api Switch
description: >
  Send or clear sticky mobile notification depending on Anker Solix Api Switch setting
trigger:
  - platform: event
    event_type: mobile_app_notification_action
    id: ActivateApi
    event_data:
      action: ACTIVATE
  - platform: state
    id: ApiDisabled
    entity_id:
      - switch.system_bkw_api_usage
    from: "on"
    to: "off"
  - platform: state
    id: ApiEnabled
    entity_id:
      - switch.system_bkw_api_usage
    to: "on"
condition: []
action:
  - variables:
      system: >
        {{device_attr(trigger.entity_id, "name") if trigger.platform == 'state' else ""}}
  - choose:
      - conditions:
          - condition: trigger
            id:
              - ApiDisabled
        sequence:
          - service: notify.thomas_handy
            alias: Nachricht an Handy
            data:
              title: Anker Api deactivated
              message: >
                {{'The Anker Solix Api for '~system~' was disabled. Launch the
                Anker App for Login and modifications, or reactivate the Api
                again.'}}
              data:
                tag: ANKERSOLIXAPI
                channel: Alarm
                ttl: 0
                priority: high
                sticky: true
                persistent: true
                color: "#FFD700"
                notification_icon: mdi:sync-alert
                actions:
                  - action: URI
                    title: App
                    uri: app://com.anker.charging
                  - action: ACTIVATE
                    title: Reactivate
      - conditions:
          - condition: trigger
            id:
              - ActivateApi
        sequence:
          - if:
              - condition: state
                entity_id: switch.system_bkw_api_usage
                state: "off"
            then:
              - alias: Reactivate the Api
                service: switch.turn_on
                target:
                  entity_id: switch.system_bkw_api_usage
                data: {}
  - if:
      - condition: trigger
        id:
          - ActivateApi
          - ApiEnabled
    then:
      - alias: Delete message on mobile
        service: notify.notify
        data:
          message: clear_notification
          data:
            tag: ANKERSOLIXAPI
            channel: Alarm
            ttl: 0
            priority: high
mode: queued
max: 3

```


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/hacs-anker-solix
[releases]: https://github.com/thomluther/hacs-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/hacs-anker-solix.svg?style=for-the-badge
[discussions]: https://github.com/thomluther/hacs-anker-solix/discussions
[discussions-shield]: https://img.shields.io/github/discussions/thomluther/hacs-anker-solix.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/hacs-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange
[buy-me-coffee]: https://www.buymeacoffee.com/thomasluthe
[integration-img]: doc/integration.png
[config-img]: doc/configuration.png
[options-img]: doc/options.png
[system-img]: doc/system.png
[inverter-img]: doc/inverter.png
[solarbank-img]: doc/solarbank.png
[connected-img]: doc/connected_devices.png
[notification-img]: doc/notification.png

