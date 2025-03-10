<div class="container">
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/07/23/iot-admin/jvwLiu0cOHjYMCwV/picl_A17X8_normal.png" alt="Smart Plug" title="Smart Plug" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/0f8e0ca7-dda9-4e70-940d-fe08e1fc89ea/picl_A5143_normal.png" alt="Anker MI80 Logo" title="Anker MI80" align="right" height="65px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/anker-power/e9478c2d-e665-4d84-95d7-dd4844f82055/20230719-144818.png" alt="Solarbank E1600 Logo" title="Anker Solarbank E1600" align="right" height="80px"/> </div>
  <div class="image"> <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/opwTD5izbjD9DjKB/picl_A17X7_normal.png" alt="Smart Meter Logo" title="Anker Smart Meter" align="right" height="65px"/> </div>
  <img src="https://public-aiot-fra-prod.s3.dualstack.eu-central-1.amazonaws.com/anker-power/public/product/2024/05/24/iot-admin/5iJoq1dk63i47HuR/picl_A17C1_normal%281%29.png" alt="Solarbank 2 E1600 Logo" title="Anker Solarbank 2 E1600"  align="right" height="80px"/> </div>
</div>

# How to use the Anker Solix Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![Discussions][discussions-shield]][discussions]

[![License][license-shield]](LICENSE)
![python badge][python-shield]


## Disclaimer

🚨 **This custom component is an independent project and is not affiliated with Anker. It has been developed to provide Home Assistant users with tools to integrate the devices of Anker Solix power systems into their smart home. Any trademarks or product names mentioned are the property of their respective owners.** 🚨


## Usage terms and conditions

This integration utilizes an unofficial Python library to communicate with the Anker Power cloud server Api that is also used by the official Anker mobile app. The Api access or communication may change or break any time without notice and therefore also change or break the integration functionality. Furthermore, the usage for the unofficial Api library may impose risks, such as device damage by improper settings or loss of manufacturer's warranty, whether is caused by improper usage, library failures, Api changes or other reasons.

🚨 **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


# Table of contents

1. **[Disclaimer](#disclaimer)**
1. **[Usage terms and conditions](#usage-terms-and-conditions)**
1. **[Device structure used by the integration](#device-structure-used-by-the-integration)**
    * [Example screenshots](#example-screenshots)
1. **[Anker account limitation and usage recommendations](#anker-account-limitation-and-usage-recommendations)**
1. **[Data refresh configuration options](#data-refresh-configuration-options)**
    * [Option considerations for Solarbank 2 systems](#option-considerations-for-solarbank-2-systems)
    * [Default options as of version 2.5.5](#default-options-as-of-version-255)
1. **[Switching between different Anker Power accounts](#switching-between-different-anker-power-accounts)**
1. **[How to create a second Anker Power account](#how-to-create-a-second-anker-power-account)**
1. **[Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting](#automation-to-send-and-clear-sticky-actionable-notifications-to-your-smart-phone-based-on-api-switch-setting)**
    * [Automation code for actionable notification](#automation-code-for-actionable-notification)
1. **[Modification of the appliance home load settings](#modification-of-the-appliance-home-load-settings)**
    * [Modification of Solarbank 2 home load settings](#modification-of-solarbank-2-home-load-settings)
    * [Care must be taken when modifying Solarbank 1 home load settings](#care-must-be-taken-when-modifying-solarbank-1-home-load-settings)
    * [Pro tips for home load automation with Solarbank 1](#pro-tips-for-home-load-automation-with-solarbank-1)
    * [Home load automation considerations for Solarbank 2](#home-load-automation-considerations-for-solarbank-2)
    * [How can you modify the home load and the solarbank schedule](#how-can-you-modify-the-home-load-and-the-solarbank-schedule)
    * [Schedule action details and limitations](#schedule-action-details-and-limitations)
1. **[Markdown card to show the defined Solarbank schedule](#markdown-card-to-show-the-defined-solarbank-schedule)**
    * [Markdown card for Solarbank 1 schedules](#markdown-card-for-solarbank-1-schedules)
    * [Markdown card for Solarbank 2 schedules](#markdown-card-for-solarbank-2-schedules)
1. **[Script to manually modify appliance schedule for your solarbank](#script-to-manually-modify-appliance-schedule-for-your-solarbank)**
1. **[Other integration actions](#other-integration-actions)**
    * [Get system info action](#get-system-info-action)
    * [Export systems action](#export-systems-action)
1. **[Showing Your Appreciation](#showing-your-appreciation)**


## Device structure used by the integration

This Home Assistant custom component integration allows seamless integration with Anker Solix devices via the Anker Api cloud.
It follows the Anker Api cloud structures, which allows registered users to define one or more Power Systems (called site in the Api) with a unique site_id.
The configured user must have defined at least one owning system, or have access to a shared system, to see devices for a configured integration account.
For each accessible system by the configured account, the integration will create one `system` device with the appropriate system sensors. These sensors typically reflect the values that are presented in the Anker mobile app main view of a system.
Following example shows how configured integration accounts may look like:

![Configured Integration][integration-img]

For each end device the system owner has configured into a system, the integration will create an End Device entry, which is assigned to the `system` device.
So far, available accessory devices such as the 0 W Output switch are not manageable on its own. Therefore they are currently presented as entity of the End Device entry that is managing the accessory.
Starting with version 2.3.0, the integration will also create one `account` device for each configuration. The `account` device has assigned all `system` devices and stand alone End Devices of your Anker account as well as some common Api entities.

### Example screenshots

Following are anonymized examples how the Anker power devices will be presented (Screenshots are from initial release without changeable entities):

  **1. System Device with Solarbank E1600 and MI80 inverter**

  ![System Device][system-img]
  ![Connected Devices][connected-img]

  **2. Solarbank E1600 Device**

  ![Solarbank Device][solarbank-img]

  **3. MI80 Inverter Device**

  ![Inverter Device][inverter-img]

  Following are screenshots from basic dashboard cards including the latest sensors and most of the changeable entities that are available when using the system main account:

  **4. Dark Theme examples of Solarbank 2 E1600 Pro with Smart Meter**

  ![System Dashboard][solarbank-2-system-dashboard-img]

  **5. Light Theme examples of Solarbank E1600**

  ![Solarbank Dashboard Light Theme][solarbank-dashboard-light-img]

  **6. Additional device preset entities only available in supported dual Solarbank E1600 systems**

  ![Dual Solarbank Entities][dual-solarbank-entities-img]

  **7. Solarbank 2 E1600 Pro device**

  ![Solarbank 2 Pro Device][solarbank-2-pro-device-img]  ![Solarbank 2 Pro Device Diag][solarbank-2-pro-diag-img]

  **8. Smart Meter device**

  ![Smart Meter Device][smart-meter-device-img]


**Note:** When using a shared system account for the integration, device detail information is limited and changes are not permitted. Therefore shared system account users may get presented no changeable and only a subset of entities by the integration.


## Anker account limitation and usage recommendations

Usage of the same Anker account in the integration and the Anker mobile app at the same time is not possible due to security reasons enforced by Anker. For more details refer to the Anker Account information in the [README](README.md).
Therefore, it is recommended to create a second account and use one in the integration and the other one in the mobile app. For instructions to create a second account and share the system, see [How to create a second Anker Power account](#how-to-create-a-second-anker-power-account).
Following is the integration configuration dialog:

![configuration][config-img]

**Attention:**

System members cannot manage any devices of the shared system or view any of their details. You can only see the system overview in the app. Likewise it is the same behavior when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

A work around to overcome this limitation for using the owning account in the HA integration has been implemented via an Api switch in the `account` device. When disabled, the integration stops any Api communication for that account. During that time, you can use the owning account again for login through the Anker app and modify device settings or perform firmware upgrades as needed. Afterwards, you can re-activate Api communication in the integration again, which will automatically re-login and continue reporting data for that account. While the Api switch is off, all sensors related to this Anker account will become unavailable to avoid reporting of stale data.

To simplify usage of this workaround, please see [Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting](#automation-to-send-and-clear-sticky-actionable-notifications-to-your-smart-phone-based-on-api-switch-setting) for an example automation, which sends a sticky mobile notification when the Api switch was disabled, using actionable buttons to launch the Anker App directly from the notification. It provides also actionable buttons to re-enable the switch again and clear the sticky notification. This avoids forgetting to re-enable your data collection once you are finished with your tasks in the Anker mobile app.


## Data refresh configuration options

The data in the cloud which can be retrieved via the Api is typically refreshed only once per minute at most. Most of the device types refresh cloud data only in 5 minute intervals. Therefore, it is recommended to leave the integration refresh interval set to the default minimum of 60 seconds, or increase it even further if no frequent updates are required. Refresh intervals are configurable from 30-600 seconds, but **less than 60 seconds will not provide more actual data and just cause unnecessary Api traffic.** Version 1.1.0 of the integration introduced a new system sensor showing the timestamp of the delivered Solarbank data to the cloud, which can help you to understand the age of the received data.

**Note:** The solarbank seems to be the only Anker system device category that provides valid timestamp data (inverter or power panel data timestamps are not updated by the cloud).

During each Api refresh interval, the power sensor values of the systems and their devices will be refreshed, along with the actual system configuration and available end devices. There are more end device details available showing their actual settings, like power cut-off, auto-upgrade, schedule, system energy statistics etc. However, those details require much more Api queries and therefore are refreshed less frequently. The device details refresh interval can be configured as a multiplier of the normal data refresh interval. With the default options of the configured account, the device details refresh will run every 10 minutes, which is typically by far sufficient. If a device details update is required on demand, each end device has a button that can be used for such a one-time refresh. However, the button will re-trigger the device details refresh only when the last refresh was more than 60 seconds ago and there is no device refresh ongoing to avoid unnecessary Api traffic.

To prevent too many requests in a short amount of time, a configurable request delay was introduced with version 1.1.1. This may be adjusted to avoid too many requests per second and potentially overload the Api or keep it busy.

The cloud Api also enforces a request limit. This request limit is applied by the cloud and is independent of the used account. It is enforced per IP address and endpoint within the last ~minute. Originally this limit was ~25 requests. As of Feb. 2025, this endpoint limit was significantly reduced by Anker to 10-12 requests per IP, endpoint and minute. Every Api client you use in your home behind the same router IP will count towards that cloud limit, like running Anker Solix HA integration clients, Anker mobile app devices etc. The mobile App may appear only unresponsive or not showing data or charts when the endpoint limit is temporarily exceeded, but in the HA integration logs you will see errors as following:
```text
2025-02-28 16:54:34.343 ERROR (MainThread) [custom_components.anker_solix] Api Request Error: 429, message='Too Many Requests', url='https://ankerpower-api-eu.anker.com/power_service/v1/site/energy_analysis'
2025-02-28 16:54:34.344 ERROR (MainThread) [custom_components.anker_solix] Response Text: {"error_msg":"Request too soon. Your actions have been recorded."}
```
If those errors occur during setup or reload of the configuration entry, you may see your configuration entry flagged with error `429: Too many requests`. Upon such errors, some or all entities may become unknown, unavailable or show stale data until further Api requests are permitted. To avoid hitting the request limit, starting with release 2.5.5 a new endpoint throttling capability was implemented to the Api client session. A default endpoint limit of 10 will be used for the throttle, which can be adjusted as required. Setting the endpoint limit to 0 will disable the throttle and provide the former client session behavior.

**Note:**

In order to avoid that potential endpoint throttling loops occurs during (re)load of the configuration while doing the initial data poll for entity creation, the initial poll of energy details is now deferred to the next data refresh cycle. This ensures fast configuration (re)loads and avoids that this process may be elongated for minute(s). This change however has the disadvantage, that energy entity creation will be delayed by one or more minutes. **So be calm and allow the integration a few minutes after restart to poll initial energy data and create the corresponding entities.**

**Important:**

The endpoint limit throttle is applied only for a single Api session. Other Api clients may query the same endpoints within last minute and therefore the integration may still exceed the endpoint limit. If you create multiple Anker configuration entries, you need to divide their endpoint limits accordingly since they can run in parallel, especially with your Anker app usage by another account.

Due to the Api endpoint limit, it is recommended to exclude the energy categories from your configuration entry if you want to avoid such request errors or the throttling delays, which aim to avoid exceeding the endpoint limit for larger or multiple systems configurations. The daily energy entities require by far the most queries to the same endpoint, and therefore may cause one or more minute throttle delays for data refreshes even in small system configurations.
Furthermore, all energy statistic entities (introduced with version 1.1.0) are excluded from new configuration entries per default. They may increase the required Api requests significantly as shown in the discussion post [Api request overview](https://github.com/thomluther/ha-anker-solix/discussions/32). Desired energy statistics can be re-enabled by removing them from the exclusion list in the configuration options.

Furthermore there may be request errors when you configured more than one Anker account (or use the Anker app in parallel) in case multiple Api requests are done in parallel from same IP address, even if that is for different accounts or systems. This is typically logged with error code 21105 as shown in following example:
```text
[custom_components.anker_solix] (21105) Anker Api Error: Failed to request. 2024-09-26 08:59:39.442 ERROR (MainThread) [custom_components.anker_solix] Response Text: {"code":21105,"msg":"Failed to request.","trace_id":"<trace_id>"}
```
Request errors may cause entities become unavailable, or even cause the configuration (re)load to fail. You cannot avoid parallel requests of multiple clients by changing the configuration options. Starting with release 2.5.5, some enhancements have been implemented to better tolerate multiple configuration entries and parallel request errors:

* Added a request retry capability to client session for Api return codes that can be classified as 'Api busy error', such as code 21105. A single retry will be attempted for the request after a random delay of 2-5 seconds, which should mask parallel request errors in most cases. A warning will be logged for the retry attempt to allow monitoring for their frequency.
* If more than one Anker configuration entry is created, the integration will try to stagger their individual data refresh polls:
    - The regular refresh interval may be delayed by 10 or more seconds to allow other active client refreshes to complete.
    - The device details refresh may be delayed by at least 2 minutes to allow other active device refreshes to complete, assuming they can run into 1-2 throttle delays. Warnings will be logged for any refresh that is being delayed.

Those enhancements should better tolerate multiple configuration entries and avoid that your entities become unavailable temporarily.

The configuration workflow was completely reworked since version 1.2.0. Configuration options can now already be modified right after successful account authorization and before the first data collection is done. Excluded device types, details categories or energy statistics can be reviewed and changed as needed. Device types of no interest can be excluded completely. Exclusion of energy categories and specific system or solarbank categories may help to further reduce the number of required Api requests and customize the presented entities of the integration.


### Option considerations for Solarbank 2 systems

Anker changed the data transfer mechanism to the Api cloud with Solarbank 2 power systems. While Solarbank 1 power systems transferred their power values every 60 seconds to the cloud, Solarbank 2 systems seem to use different intervals for Api cloud updates:
   - Default interval is **~5 minutes**: After ~60 seconds, the cloud considered the last values obsolete at initial product release. That resulted in no longer returning valid values upon refresh requests (only 0 values), until new values have been received again from the devices. There was a change implemented in the cloud around 25. July 2024 to provide always the last known data upon Api refresh requests. This eliminated the missing value problem for shared accounts in the Anker mobile app or 0 values in any api client responses.
   - Triggered interval is **~3 seconds**: When the mobile app is used with the main account, it triggers permanent Api cloud updates, most likely via the MQTT cloud server connection to the device. The same method is used for triggering live data updates of individual devices when watching device real time data. That means while watching the Solarbank 2 power system overview via main account in the anker app, you receive very frequent data updates from the cloud Api. Of course, this is only applied while the home screen is watched to limit cloud Api requests, data traffic and device power consumption for the remaining times.

In consequence, before the cloud change in July 2024, the HA integration typically received 1 response with valid data and another 4 responses with invalid data when using the default refresh interval of 60 seconds. **There is nothing the integration or the underlying Api library can do to trigger more frequent cloud data updates for Solarbank 2 systems**. Per default, the HA integration switched all relevant entities to unavailable while invalid data is returned. Optionally, you can change your integration configuration options to **Skip invalid data responses**, which will maintain the previous entity value until valid data is received again. While this means your entities will not become unavailable most of the time, they may present obsolete/stale data without your awareness. It is your choice how entities should reflect data that are marked invalid in the Api response, but neither of the options makes the data more current or reliable. The SB data time entity in the system device will reflect when the last data was provided by the Solarbank 2, or when the last valid data was read through the Api, since also that timestamp in the response is not always valid even if the data itself is valid. A new [action was implemented](#get-system-info-action) to assist you with a manual verification capability of available system data and power values in the cloud.

Note:

The cloud change in July 2024 did not change the cloud data update frequency for Solarbank 2 systems. It only avoids that the cloud considers older device data as obsolete, but always responds with last known data instead. It has the same effect as the new 'Skip invalid data responses' option that was implemented to the integration.

### Default options as of version 2.5.5

![Options][options-img]

**Note:** Prior version 1.2.0, when you added categories to the exclusion list, the affected entities were removed from the HA registry during integration reload but they still showed up in the UI as entities no longer provided by the integration. You had to remove those UI entities manually from the entity details dialog.
Starting with version 1.2.0, a change in the exclusion list that added more exclusions will completely remove the affected devices and re-register them with remaining entities as necessary. This avoids manual cleanup of excluded entities.


## Switching between different Anker Power accounts

The integration will setup the entities with unique IDs based on device serials or a combination of serial numbers. This makes them truly unique and provides the advantage that the same entities can be re-used after switching the integration configuration to another shared account. While the entity history is not lost, it implies that you cannot configure different accounts at the same time when they share a system. Otherwise, it would cause HA setup errors because of non unique entities. Therefore, new integration configurations are validated and not allowed when they share systems or devices with an active configuration.
Up to release 2.1.0, if you wanted to switch between your main and shared account, you had to delete first the active configuration and then create a new configuration with the other account. When the devices and entities for the configured account will be created, deleted entities will be re-activated if their data is accessible via Api for the configured account. That means if you switch from your main account to the shared account, only a subset of entities will be re-activated. The other deleted entities and their history data may remain available until your configured HA recorder interval is over. The default HA recorder history interval is 10 days.

Starting with HA 2024.04, there is a new option to reconfigure an active integration configuration. This integration reconfiguration capability has been implemented with integration version 2.1.0 and allows a simplified, direct account reconfiguration from the integration's menu as shown in following example:
![Reconfigure][reconfigure-img]

**Note:**

While changing your active configuration to another account, the same actions and validations will be performed in background as via configuration entry deletion and re-creation. Using another account that shares any system or device with any active configuration except the modified one is not allowed. Once the configuration change is confirmed for the new or same account, all devices and entities will be unregistered and therefore removed, and afterwards recreated to adjust for the manageable entities of that modified account. Confirming a reconfiguration to the same account can therefore be used as workaround to clear orphaned entities. Those can occur when you recreate or reconfigure your power systems in the Anker app or change alias names for existing devices, since that alias name is used for automated entity_id generation.


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
  1. Just now you can access the system as a member. The owner will also get a confirmation that you accepted the invitation.


## Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting

Following automation can be used to send a sticky actionable notification to your Android mobile when the HA companion app is installed. It allows you to launch the Anker app or to re-activate the Api again for your HA integration configuration.

![notification][notification-img]

Make sure to replace the entities used in the example below with your own entities. The system variable is automatically generated based on the device name of the entity that triggered the state change.

**Note:** If you want to modify the notification to work with your iPhone, please refer to the [HA companion App documentation](https://companion.home-assistant.io/docs/notifications/notifications-basic/) for IOS capabilities.

<details>
<summary>Expand to see automation code</summary>

### Automation code for actionable notification

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
      - switch.accountalias_country_api_usage
    from: "on"
    to: "off"
  - platform: state
    id: ApiEnabled
    entity_id:
      - switch.accountalias_country_api_usage
    to: "on"
condition: []
action:
  - variables:
      account: >
        {{device_attr(trigger.entity_id, "name") if trigger.platform == 'state' else ""}}
  - choose:
      - conditions:
          - condition: trigger
            id:
              - ApiDisabled
        sequence:
          - service: notify.my_smartphone
            alias: Send notification to smartphone
            data:
              title: Anker Api deactivated
              message: >
                {{'The Anker Solix Api for '~account~' was disabled. Launch the
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
                entity_id: switch.accountalias_country_api_usage
                state: "off"
            then:
              - alias: Reactivate the Api
                service: switch.turn_on
                target:
                  entity_id: switch.accountalias_country_api_usage
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
</details>


## Modification of the appliance home load settings

### Modification of Solarbank 2 home load settings

Version 2.1.0 of the integration fully supports switching between `Smart Meter` (AI) or `Manual` (custom) home load usage modes when a smart meter is configured in the system. Otherwise only `Manual` usage mode is supported. Version 2.2.0 also supports the `Smart Plug` usage mode once smart plugs are configured in your Anker power system. Furthermore, the output preset can be adjusted directly, which will result in changes to the schedule rate plan applied to the solarbank. A preset change is only applied to the current time interval in the corresponding rate plan and if none exists, the rate plan or a current time interval will be created. Furthermore, all schedule actions now support modifications of any schedule rate plans, plan intervals and weekdays if supported by the rate plan.

Version 2.2.0 added support for the smart plug usage mode. When this mode is active, another blend plan will be used to customize additional base load that should be added to the measured smart plug total power. The number entity that changes the output preset will therefore modify the actual time slot in the blend plan when the smart plug usage mode is active. Otherwise it will modify the actual time slot of the custom rate plan. The added system entity for `other load power` will reflect the actual extra power added based on the blend plan settings when smart plug usage mode is active. The system output preset sensor will reflect only the current setting from the custom rate plan, however this will not be applicable during smart plug usage mode.

### Modification of Solarbank 2 AC settings

The Solarbank 2 AC model has pretty much the same setting capabilities as the other SB2 device models, and it comes with new and AC charge unique features.
Version 2.5.0 of the integration provided initial support for the additional features that are unique to the AC models. Those features are:
  - Manual backup charge Option
    A start and end date and time can be defined when the SB2 AC should be charged from grid with max. power, that is 1000/1200 W depending on installed battery packs and temperature. A separate switch allows to deactivate a backup interval to disable an active backup mode or 'remove' a future interval. Whenever the defined interval is enabled and SB2 device time reaches the interval, the backup mode is enabled with priority over any active set usage mode. The SB2 returns to the previous defined usage mode once the backup mode is finished, either by disabling the mode manually, by exceeded end time or by full SOC that does not allow further charging.
  - Usage Time mode
    A Use Time plan must be defined first before this mode can be enabled. The Use Time plan defines per season (range of months), at which hours during the day you have which power tariff. You can define peek, medium peek and off peek tariffs, as well as another tariff that seems to be considered as 'lowest' tariff. For each tariff you have to define the price as well. The daily intervals are typically the same for each day, unless you specify that weekends should be different to normal weekdays. This Use Time plan is considered in the Usage Time mode for doing 'Peek and Valley' shaving. While I have no experience with that mode, I assume this will do (maximum?) AC charge during off peek and other periods, while doing discharge during peek times. Currently there does not seem to be an option to define the maximum charge, nor to feed the actual tariffs dynamically by any actual power market price Apis. This mode can be used only in combination with a Smart Meter or Smart Plugs, which can provide the home demand for allowing automatic discharge regulation during the peek intervals.
  - Toggling system price type setting
    So far, only a single fixed price could be defined for your Solarbank 2 system, which is used by the Anker Cloud to calculate your overall savings. Once you have defined a Use Time plan with different tariffs, the system price type can be toggled to the defined Use Time plan tariffs. This is then hopefully making better total saving calculations, but this is difficult to validate. It turned out, that enabling the Usage Time mode will automatically toggle the system price type to Use Time plan. However, toggling away from Usage Time mode does not automatically revert system price type back to fixed price. And it also might not make sense to use a fixed price once you have defined a Use Time plan with your 'well known' tariffs.

The integration actually supports toggling to the new modes, as well as modifying the backup charge option date times and switch. However, modification or definition of a Use Time plan is not supported at this point (It may come in a future release). Furthermore, there are currently no actions available yet for customizing any of the AC usage mode options. The backup option can be modified only via control entities, which also represent the actual defined settings. In order to avoid that each control entity change triggers an Api call, following behavior was implemented for the backup mode:
  - The UI datetime entities trigger value updates in each field change (date, hour, minute), which may result in 3 value updates for a single entity.
  - Typically multiple entities need to be modified before before the final backup interval definition is completed
  - If any of the backup control entities is changed, the backup switch entity will always be disabled and all changes will only be applied to the Api cache
  - Only re-enabling the backup switch will actually trigger the Api call to update the whole backup interval with the settings available in the cache. This should be made last and once all interval definitions are done to save the new interval via the Api
  - The App does not allow to define a backup datetime in the past, and the end time must be later than start time. These logical corrections will also be applied upon  entity changes in the integration.
  - For convenience, the backup interval will automatically be set for the next 3 hours from now when invalid datetime values are given
    - This is sufficient to fully charge an AC device with an expansion battery
    - The backup mode will automatically being disabled when 100 % SOC is reached
  - You can also immediately enable the backup mode, just by enabling the backup switch entity or by selecting the Backup Charge mode.
    - When selecting the Backup Charge mode, the backup will always start immediately
    - If there is still a valid end time in the future, this will be used instead of using the default end time in 3 hours from now
    - When enabling the backup switch, it will only apply the current backup interval via Api. If the end time is passed, the default of 3 hours is applied from now.
  - If a longer or shorter immediate backup interval is required, you just need to modify the end time and re-enable the backup switch.

Important:
  - The schedule in the Api cache is refreshed automatically with each device details refresh interval (10 minutes by default option settings). It may reset any temporary Api cache changes that have been made with the backup mode controls before they have been applied via an Api call.
  - The Usage Mode selector extracts the supposed active state from the schedule object, based on actual HA server time. That means it represents the supposed active mode when system time falls into an enabled backup interval. If there are time offsets between your HA server and the Solarbank, the supposed state in the Usage Mode selector entity may be wrong.
  - The Solarbank 2 also reports the active usage mode as system sensor which has been added with version 2.5.0. However, due to the large delay of up to 5 minutes until the solarbank reports data updates to the cloud, you can observe significant delays of applied usage mode changes.


### Care must be taken when modifying Solarbank 1 home load settings

**Attention:**

**Setting the Solarbank 1 output power for the house is not as straight forward as you might think and applying changed settings may give you a different result as expected or as represented by the output preset sensor.**

Following is some more background on this to explain the complexity. The home load power cannot be set directly for the Solarbank. It can only be set indirectly by a time schedule, which typically covers a full day from 00:00 to 24:00h. There cannot be different schedules on various days for Solarbank 1, it's only a single schedule that is shared by all solarbanks configured into the system. Typically for single solarbank systems, the solarbank covers the full home load that is defined for the time interval. For dual solarbank setups, both share 50% of the home load power preset per default. This share was fixed and could not be changed so far. Starting with the Anker App 2.2.1 and new solarbank firmware 1.5.6, the share between both solarbanks can also be modified. Starting with integration version 1.3.0, this capability is also supported with additional entities that will be created for dual solarbank systems supporting individual device presets. It is a new preset mode that was implemented in the schedule structure. Integration version 2.4.0 added support for a new discharge priority switch, which is supported for solarbank 1 with firmware 2.0.9 or higher. This allows to prioritize discharge over PV production for the power export to the house. When the Solarbank 1 will discharge, no PV production or direct bypass is possible anymore, but the requested load power according to the schedule will be discharged from the battery.

Following are the customizable parameters of a time interval that are supported by the integration and the Python Api library:
  - Start and End time of a schedule interval
  - Appliance home load preset (0/100 - 800/1600 W). If changed in dual solarbanks systems, it will always use normal preset mode with the default 50% device share. Solarbank 2 devices support lower settings down to 0 W, while Solarbank 1 devices support min. 100 W
  - For Solarbank 2 only (ignored for Solarbank 1 systems):
      - Schedule plan to be used for the time interval
      - Week days to be  used for the time interval
  - For Solarbank 1 only (ignored for Solarbank 2 systems):
      - Device load preset (50-800 W) for dual solarbank systems supporting individual device presets. A change will always enable advanced preset mode and also affect the appliance load preset accordingly.
      - Export switch
      - Charge Priority Limit (0-100 %), typically only seen in the App when Anker MI80 inverter is configured
      - Discharge priority switch, requires Solarbank 1 firmware 2.0.9 and HA integration 2.4.0

The given ranges depend on the number of solarbanks in the system and are being enforced by the integration and the Api library. However, while those ranges are also accepted by the appliance when provided via a schedule, the appliance may ignore them when they are outside of its internally used/defined boundaries. For example, you can set an Appliance home load of 100 W which is also represented in the schedule interval. The appliance however will still apply the internal minimum limit of 150 W depending on the configured inverter type for your solarbank.
It is typically the combination of those settings, as well as the actual situation of the battery SOC, the temperature and the defined/used inverter in combination with either the charge priority setting or activation of the 0 W switch that all determine which home load preset will be applied by a Solarbank 1 appliance. The applied home load is typically represented in the App for the active time interval, and this is what you can also see in the Solarbank System sensor for the preset output power. But rest assured, even if it shows 0 W home load preset is applied, it does not warrant you there won't be any output power to the house!

**To conclude: The appliance home load preset for Solarbank 1 is just the desired output, but the truth can be completely different**

Before you now start using the home load preset modification capability in some fancy real time automation for zero grid power export, here is my advise:

  - **Be careful !!!**

I will also tell you why:
  - The first generation of Solarbank E1600 is Anker's first all in one battery device for 'balcony solar systems' and was not designed for frequent home load changes. Unlike the new Solarbank 2 systems, Solarbank 1 is only manageable via a 'fixed' time schedule and therefore was never designed to react quickly on frequent home load changes (and neither is the Api designed for it)
  - The Solarbank reaction on changed home load settings got better and during tests a typical adoptions of 10-20 seconds for smaller home load changes with firmware 1.5.6 have been observed. However, using only the integration sensors is still far too slow for real/near time power automation, since all data communication occurs only via the cloud and has significant value time lags to be considered.
  - In reality (as an average) you need to allow the solarbank up to 1-2 minutes until you get back reliable sensor values from the cloud that represent the result of a previous change. The solarbank also sends the data only once per minute to the cloud, which is another delay to factor into your automation.
  - If you have additional and local (real time) sensors from smart meters or inverters, they might help to see the modification results faster. But still, the solarbank needs time until it settled reliably for a changed home load. Furthermore it all depends on the cloud and internet availability for any automation. Alternatively I recommend to automate the solarbank discharge only locally via limiting the inverter when you have real time automation capabilities for your inverter limits. [I realized this project as described in the forum](https://community.home-assistant.io/t/using-anker-solix-solarbank-e1600-in-ha/636063) with Hoymiles inverter, OpenDTU and a Tasmota reader device for the grid meter and that works extremely well.
    - **Attention:** Don't use the inverter limit during solar production since this will negatively impact your possible solar yield and the solarbank may end up in crazy power regulations all the time.
  - Additionally, each schedule parameter or complete schedule change requires 2 Api requests, one to submit the whole changed schedule and another two to query the applied and resulting schedule and site values again for sensor updates. To enforce some protection for the Api and accommodate the slow solarbank reaction, an increase of the home load is just allowed every 30 seconds at least (decreases or other interval parameter changes are not limited)
    - **Attention:** Cloud Api requests are limited, but actually the enforced limits in regards to quantity and time frames are unknown. Each change may bring you towards the enforced limit and not only block further changes, but also render all integration entities unavailable or stale
  - If you have some experience with the solarbank behavior, you may also know how weird it sometimes reacts on changed conditions during the day (or even unchanged conditions). This makes it difficult to adjust the home load setting automatically to a meaningful value that will accomplish the desired home load result.
  - If you plan to automate moderate changes in the home load, use a timer helper that is restarted upon each change of the settings and used as condition for validation whether another change (increase) should be applied. I would not recommend to apply changes, especially increases in the home load, in less than 2 minute intervals, a trusted re-evaluation of the change results and further reaction can just be done after such a delay. Remember that each provided Solarbank data point is just a single sample within 60 seconds or more. The value average in that interval can be completely different, especially if you compare Solarbank data with real time data of other power devices in your home!

Meaningful automation ideas that might work for the Solarbank 1:
  - Use schedule actions to apply different set of schedules for different weekdays (workday, home office, weekend etc). The Anker App does not provide this capability, but with HA automation you could create new schedules for given days in advance. Use first the Set schedule action which will create a new all day interval and then Update schedule action to insert additional intervals as needed. Try the action sequence manually to validate if they accomplish the desired end result for your schedule.
  - Use solar forecast data to define a proper home load preset value for the day in order to allow the battery charging is spanning over the whole day while using as much direct solar power as possible in the house. This will prevent that the battery is full before noon in summer and then maximum solar power is bypassed to the house but cannot be consumed. This is something that I plan implementing for this summer since I have already built an automation for recommended home load setting...
  - Use time to time changes in the home load when you have expected higher consumption level for certain periods, e.g. cooking, vacuum cleaning, fridge cooling, etc. Basically anything that adds a steady power consumption for a longer period. Don't use it to cover short term consumers like toaster, electric kettles, mixer or coffee machines. Also the home load adoption for washing machines or laundry dryer might not be very effective and too slow since they are pretty dynamic in power consumption.
  - You have probably more automation ideas for your needs and feel free to share them with the community. But please keep the listed caveats in mind to judge whether an automation project makes sense or not. All efforts may be wasted at the end if the appliance does not behave as you might expect.

### Pro tips for home load automation with Solarbank 1

If you are interested building your own automation for using the Solarbank 1 as surplus battery buffer without wasting generated solar energy to the grid unnecessarily, you may have a look to my [automation project that I documented in the discussions](https://github.com/thomluther/ha-anker-solix/discussions/81).


### Home load automation considerations for Solarbank 2

For Solarbank 2 systems with a smart meter, you can automate the switch of the home load usage mode between `Smart Meter`, `Manual` and `Smart plugs` if you may have the need to change this in your setup. If you have the AC model, you can also switch to `Backup charge` and `Usage time` mode if applicable in your system setup. The Anker mobile app actually does not support scheduled switches of the home load usage mode.
Furthermore you can automate the manual appliance output preset, however this will only be applied when the `Manual` usage mode is active.
The same is possible with the additional base power that should be added to smart plug power while `Smart plug` usage mode is active.
The integration has built-in the same cool down of 30 seconds for subsequent increases of the output preset in order to limit the number of Api requests and schedule changes pushed by HA automation.

**Important:**

It may take up to 5-6 minutes until you can seen the effect of usage plan or control changes via the integration. This is not a slow reaction of the device or the integration, but the 5 minute interval used by Solarbank 2 to report its latest data to the cloud.

---
**At this point be warned again:**

**The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library.**

---

### How can you modify the home load and the solarbank schedule

Following 3 methods are implemented to modify the home load, the schedule and/or the usage mode of your Solarbank.

**Important:**

All methods require that the HA integration is configured with the owner account of your system, otherwise the defined schedule for system devices cannot be accessed.

#### 1. **Direct parameter changes via entity modifications for Appliance and/or Device Home Load preset, allowance of export, charge priority limit, discharge priority or usage mode**

Any change in those entities is immediately applied to either the current time slot in the active schedule plan, or to the general schedule structure. Please see the Solarbank dashboard screenshots above for examples of the entity representation. While the schedule is shared for the appliance, each Solarbank 1 in a dual Solarbank setup will be presented with those entities. A change in the device load preset will however enable advanced preset mode and only change the corresponding solarbank output. However, it will also result in a change of the appliance home load preset accordingly.

Solarbank 2 schedules have different plans which may be using the same or different formats. Their plan format typically has less time interval settings as for Solarbank 1 appliances and they can only define the appliance output power. However, different Solarbank 2 time schedules can be defined for various weekdays in each plan. One common setting for all plans is the solarbank 2 usage mode. If a smart meter or smart plugs are configured in your power system, you can set the usage mode to Smart Meter or Smart plugs and the Solarbank 2 will automatically adjust the appliance output to your house or smart plug demand as measured by the devices. So while you can still define a custom output schedule via the Anker mobile app, it may be applied ONLY if the solarbank lost connection to the device that is used to provide automated power demand such as the smart meter. For any gap in the defined custom plan, the default output of 200 W will be applied.
For smart plug usage mode the blend plan schedules will be used to add base power to smart plug measured power.
The AC model also support a backup charge interval definition as well as a Use Time plan (Use Time plan modifications are not supported yet by the integration)

**A word of caution:**

When you represent the home load number entities as input field in your dashboard cards, do **NOT use the step up/down arrows** but enter the home load value directly into the field. Each step/click via the field arrows triggers a setting change via Api call immediately, and increases are restricted for at least 30 seconds intervals. Preferably use a slider for manual number modifications, since the value is just applied to the entity once you release the slider movement in the UI (do not release the slider until you moved it to the desired value).
Datetime entities in the UI are even worse, they trigger value updates for each field that is changed (date, hour, minute). To prevent Api calls upon each field change, any backup interval modification is only sent via Api once you enable the backup switch.

#### 2. **Solarbank schedule modifications via actions**

Schedule actions are useful to apply manual or automated changes for periods that are beyond the current time interval. Following actions are available:

  - **Set new Solarbank schedule:**

    Allows wiping out the existing time intervals in the selected or active plan and defines a new time interval with the customizable schedule parameters above.

  - **Update Solarbank schedule:**

    Allows inserting/updating/overwriting a time interval in the active or selected schedule plan with the customizable schedule parameters above. Adjacent intervals will be adjusted automatically.

  - **Request Solarbank schedule:**

    Queries the actual schedule and returns the whole schedule JSON object, which is also provided in the schedule attribute of the Solarbank device output preset sensor.

  - **Clear Solarbank schedule:**

    Clear all defined solarbank schedule time intervals. The solarbank will have no longer a schedule definition and use the default output preset all day (200 W). For solarbank 2, you can optionally clear the defined intervals only for the specified weekdays of the active or specified plan.

You can specify the solarbank device ID or the entity ID of the solarbank output preset sensor as target for those actions. The Action UI in HA developer tools will filter the devices and entities that support the solarbank schedule actions. I recommend using the entity ID as target when using the action in automations, since the device ID is an internal registry value which is difficult to map to a context. In general, most of the solarbank schedule changes should be done by the update action since the Api library has built in simplifications for time interval changes. The update action follows the insert methodology for the specified interval using following rules:
  - Adjacent slots are automatically adjusted with their start/end times
    - Completely overlay slots are automatically removed
    - Smaller interval inserts result in 1-3 intervals for the previous time range, depending on the update interval and existing interval time boundaries
    - For example if the update interval will be within an existing larger interval, it will split the existing interval at one or both ends. So the insert of one interval may result in 2 or 3 different intervals for the previous time range.
  - New gaps will not be introduced by schedule updates, but existing gaps will remain if outside of the specified interval
  - If only the boundary between intervals needs to be changed, update only the interval that will increase because updating the interval that shrinks will split the existing interval
    - When one of the update interval boundaries remains the same as the existing interval, the existing interval values will be re-used for the updated interval in case they were not specified.
    - This allows quick interval updates for one boundary or specific parameters only without the need to specify all parameters again
  - All interval parameters are mandatory for a schedule update via the Api. If they are not specified with the action, existing ones will be re-used when it makes sense or following defaults will be applied:
    - 100 W Appliance Home load preset in normal preset mode if neither appliance nor device load presets are provided
    - Current weekday or existing plan with current weekday if no weekdays provided (Solarbank 2 only)
    - Allow Export is ON (Solarbank 1 only)
    - 80 % Charge Priority limit (Solarbank 1 only)
    - Discharge Priority switch is OFF (Solarbank 1 only)
  - The Set schedule action also requires to specify the time interval for the first slot. However, testing for Solarbank 1 has shown that the provided times are ignored and a full day interval is always created when only a single interval is provided with a schedule update via the Api. For Solarbank 2, the first set slot behavior may be different.

For Solarbank 2 systems, following weekday rules will be applied:
  - When no weekdays are provided, the current weekday will be used.
    - If no schedule exists yet, all weekdays will be used.
  - When a plan exists already containing the current weekday, this plan will be modified
  - When weekdays are provided, they are considered as following:
    - If an existing plan is a complete subset of provided weekdays, this plan will be re-used. Extra provided days will be added to the plan.
    - If an existing plan is no complete subset of provided weekdays, the first plan with most overlapping days will be cloned and modified as new plan for the provided weekdays.
  - For the clear schedule action, only the provided weekdays will be removed from existing plans
  - Any existing plan will be curated to avoid that same weekday is defined in different plans
    - Empty plans will be removed from the schedule

For Solarbank 2 systems, following plan rules will be applied:
  - When no plan is provided, the plan used by the active usage mode will be used.
    - If the active plan is not valid for the action, the manual plan will be used.
  - When a plan is selected, the selected plan will be modified.
    - This allows modification of a plan that is currently not in use

For dual Solarbank 1 systems, following load preset rules will be applied:
  - If only appliance load preset provided, the normal preset mode will be used which applies a 50% share to both solarbanks
  - If only device load preset provided, the advanced power mode will be used if supported by existing schedule structure. The appliance load preset will be adjusted accordingly, but the other solarbank device preset will not be changed. It will fall back to normal appliance load usage if advanced power mode not supported by existing schedule structure.
  - If appliance and device load preset are provided, the advanced power mode will be used if supported by existing schedule structure. The appliance load preset will be used accordingly within the capable limits, resulting from the provided device preset and the preset difference that will be applied to the other solarbank device. It will fall back to normal appliance load usage if advanced power mode not supported by existing schedule structure.
  - If neither appliance nor device presets are provided, the existing power presets and mode will remain unchanged and reused if at least start or end time remain unchanged. Otherwise the default preset will be applied for the interval
  - If only device preset is provided for single solarbank systems, it will be applied as appliance load preset instead, which in fact is the same result for such systems

For combined Solarbank 2 and Solarbank 1 systems, following schedule rules will be applied:
  - SB1 schedule plans and control entity changes will only be applied when required entities are available. That means the SB2 usage mode must NOT be in manual mode.
  - When SB1 control entities are unavailable, their presentation in the UI may be confusing and appear as still allowing value changes
    - For instance unavailable number entity slider will show the middle value of the defined range and allow modifications. However, those changes will never be applied and reset upon next panel refresh
  - When SB2 mode is an automatic mode, the normal SB1 schedule will be used and you should even be able to set different device output power for dual SB1 device attached to a single SB2
  - While the SB2 is active in manual mode, it will enforce another SB1 schedule and always control the SB1 output preset, with a fixed share of 50% in dual SB1 setups

Note:

Usage of Solarbank 1 advanced preset mode is determined by existing schedule structure. When no schedule is defined and the set schedule action is used with a device preset requiring the advanced power preset mode, but both solarbank 1 are not on required firmware level to accept the new schedule structure, the action call may fail with an Api request error.

#### 3. **Interactive solarbank schedule modification via a parameterized script that executes a schedule action with provided parameters**

Home Assistant 2024.3 provides a new capability to define fields for script parameters that can be filled via the more info dialog of the script entity prior execution. This allows easy integration of schedule modifications to your dashboard (see [Script to manually modify appliance schedule for your solarbank](#script-to-manually-modify-appliance-schedule-for-your-solarbank)).


### Schedule action details and limitations

Following are screenshots showing the schedule action UI panel (identical for Set schedule and Update schedule action), and the Get schedule action with an example:

**1. Set or Update schedule action UI panel example, using the entity as target**

![Update schedule service][schedule-service-img]

**2. Get schedule action example, using the device as target**

![Get schedule service][request-schedule-img]


While not the full value ranges supported by the integration can be applied to the device, some may provide enhanced capabilities compared to the Anker App. Following are important notes and limitations for schedule modifications via the cloud Api:

  - Time slots can be defined in minute granularity and what I have seen, they are also applied (don't take my word for given)
  - The end time of 24:00 must be provided as 23:59 since the datetime range does not know hour 24. Any seconds that are specified are ignored
  - Home Assistant and the Solarbank should have similar time, but especially same timezone to adopt the time slots correctly. Even more important it is for finding the current/active schedule time interval where individual parameter changes must be applied
    - Depending on the front end (and timezone used with the front end), the time fields may eventually be converted. All backend datetime calculations by the integration use the local time zone of the HA host. The HA host must be in the same time zone the Solarbank is using, which is typically the case when they are on the same local network.
  - Situations have been observed during testing with solarbank 1, where an active home load export was applied in the schedule, but the solarbank 1 did not react on the applied schedule. While the cloud schedule was showing the export enabled with a certain load set, verification in the Anker App presented a different picture: There the schedule load was set to **0 W in the slider** which is typically not possible in the App...The only way to get out of such weird schedules on the appliance is to make the interval change via the Anker App since it may use other interfaces than just the cloud Api (Bluetooth and another Cloud MQTT server). This problem was only noticed when just a single resulting interval remains in the schedule that is sent via the Api, for example setting a new schedule or making an update with a full day interval. To avoid this problem, make sure your schedule has more than one time interval and you do NOT use the Set new Solarbank schedule action. Instead you can apply schedule changes via the Update Solarbank schedule action which is NOT covering the full day.


## Markdown card to show the defined Solarbank schedule

### Markdown card for Solarbank 1 schedules

Following markdown card code can be used to display the solarbank 1 schedule in the UI frontend. The active interval will be highlighted. Just replace the entity with your sensor entity representing solarbank effective output preset. It is the sensor that has the schedule attribute.

![markdown-card][schedule-markdown-img]

<details>
<summary><b>Expand to see card code</b><br><br></summary>

#### Markdown card code for Solarbank 1 schedules

```
type: markdown
content: |
  ## Solarbank 1 Schedule

  {% set entity = 'sensor.solarbank_e1600_home_preset' %}
  {% set slots = (state_attr(entity,'schedule')).ranges|default([])|list %}
  {% set isnow = now().time().replace(second=0,microsecond=0) %}
  {% if slots %}
    {{ "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s"|format('Start', 'End', 'Preset', 'Export', '▼Prio', '▲Prio', 'Mode', 'SB1', 'SB2', 'Name') }}
    {{ ":---:|:---:|---:|:---:|:---:|:---:|:---:|---:|---:|:---" }}
  {% else %}
    {{ "No schedule available"}}
  {%- endif -%}
  {%- for slot in slots -%}
    {%- set bs = '_**' if strptime(slot.start_time,"%H:%M").time() <= isnow < strptime(slot.end_time.replace('24:00','23:59'),"%H:%M").time() else '' -%}
    {%- set be = '**_' if bs else '' -%}
    {%- set sb2 = '-/-' if slot.device_power_loads|default([])|length < 2 else slot.device_power_loads[1].power~" W" -%}
      {{ "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s"|format(bs~slot.start_time~be, bs~slot.end_time~be, bs~slot.appliance_loads[0].power~" W"~be, bs~'On'~be if slot.turn_on else bs~'Off'~be, bs~'On'~be if slot.priority_discharge_switch else bs~'Off'~be, bs~slot.charge_priority~' %'~be, bs~(slot.power_setting_mode or '-')~be, bs~slot.device_power_loads[0].power~" W"~be, bs~sb2~be, bs~slot.appliance_loads[0].name)~be }}
  {% endfor -%}
```
</details>

**Notes:**
- Shared accounts have no access to the schedule
- The schedule control entities show the individual customizable settings per interval. The reported home load preset that is 'applied' and shown in the system preset sensor state as well as in the Anker App is a combined result from the appliance for the current interval settings.
- The applied appliance home load preset can show 0 W even if appliance home load preset is different, but Allow Export switch is off. It also depends on the state of charge and the charge priority limit and the defined/installed inverter. Even if the preset sensor state shows 0 W, it does not mean that there won't be output to the house. It simply reflects the same value as presented in the App for the current interval.
- Starting with Anker App 2.2.1, you can modify the default 50 % preset share between a dual Solarbank setup. The SB1 and SB2 values of the schedule will show the applied preset per Solarbank in that case, which is also reflected in the individual device preset sensor. For single Solarbank setups, the individual device presets of the schedule are ignored by the appliance and the appliance preset is used.
- Even if each Solarbank device has its own Home Preset sensor (reflecting their contribution to the applied home load preset for the device) and schedule attribute, all Solarbanks in a system share the same schedule. Therefore a parameter change of one solarbank also affects the second solarbank. The applied home load settings are ALWAYS for the schedule, which is still shared by all solarbanks in the system.
- The schedule structure for the normal preset mode is always reflecting 50% of the appliance load preset to the device load preset. This is also the case for single solarbank systems. A simple schedule structure rule is that with no or normal preset mode, the appliance load preset will be applied. For advanced preset mode which is only accepted in dual solarbank systems, the individual device load presets will be applied and the appliance load setting will be ignored.
- Starting with Anker App 3.3.0 and Firmware 2.0.9, you can enable discharge priority. This is also supported in the HA integration 2.4.0. If not all solarbanks in your system are at the required version, the discharge priority setting will have no effect and the switch entity may not be presented by the integration.

### Markdown card for Solarbank 2 schedules

Following markdown card code can be used to display the Solarbank 2 schedule in the UI frontend (including custom_rate_plan, blend_plan, use_time plan and manual_backup plan if defined). The active interval in the active plan will be highlighted. Just replace the entities at the top with your sensor entities representing the solarbank output preset and usage mode.

**Attention:**
The markdown card is very sensitive for proper formatting of printed characters. Markdown tables may not be correctly formatted if indents are wrong, for example caused by indents of the template code.


![markdown-card][schedule-2-markdown-img]

<details>
<summary><b>Expand to see card code</b><br><br></summary>

#### Markdown card code for Solarbank 2 schedules

```
type: markdown
content: >
  {% set entity = 'sensor.solarbank_2_e1600_ac_home_preset' %}
  {% set mode = state_translated('select.solarbank_2_e1600_ac_usage_mode') %}
  {% set schedule = state_attr(entity,'schedule')|default({}) %}
  {% set plan = ((state_attr(entity,'schedule')).custom_rate_plan|default([]))|list %}
  {% set isnow = now().replace(second=0,microsecond=0) %}
  ### SB2 Schedule (Set Usage Mode: {{mode|capitalize}})
  {% for plan_name,plan in (schedule or {}).items() %}
    {% if plan_name in ['custom_rate_plan','blend_plan'] and plan -%}
      {%- set week = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"] -%}
      {%- set active = (mode=='smartplugs' and plan_name=='blend_plan') or (mode!='smartplugs' and plan_name!='blend_plan')-%}
    {{ "%s | %s | %s | %s | %s"|format('ID', 'Start', 'End', 'Preset', 'Weekdays ('+plan_name+')') }}
    {{ ":---|:---|:---|:---:|:---" }}
      {%- for idx in plan -%}
        {%- set index = idx.index|default('--') -%}
        {%- for slot in idx.ranges|default([]) -%}
          {%- set ns = namespace(days=[]) -%}
          {%- for day in idx.week|default([]) -%}
            {%- set ns.days = ns.days + [week[day]] -%}
          {%- endfor -%}
          {%- set bs = '_**' if strptime(slot.start_time,"%H:%M").time() <= isnow.time() < strptime(slot.end_time.replace('24:00','23:59'),"%H:%M").time() and int(isnow.strftime("%w")) in idx.week|default([]) and active else '' -%}
          {%- set be = '**_' if bs else '' %}
    {{ "%s%s | %s | %s | %s | %s"|format(bs~index~be,'*' if bs else '', bs~slot.start_time~be, bs~slot.end_time~be, bs~slot.power~" W"~be, bs~','.join(ns.days)~be) }}
        {%- endfor %}
      {%- endfor %}
    {%- endif %}
    {#- AC specific plans -#}
    {% if plan and plan_name in ['manual_backup'] %}
      {% set switch = plan.switch|default(false) %}
    {{ "%s | %s | %s"|format('Start Time', 'End Time', 'Switch: ' + ('ON' if switch else 'OFF') + ' ('+plan_name+')') }}
    {{ ":---|:---|:---" }}
      {%- for idx in plan.ranges|default([]) %}
        {%- set start = idx.start_time|as_datetime|as_local -%}
        {%- set end = idx.end_time|as_datetime|as_local -%}
        {%- set bs = '_**' if switch and start.time() <= isnow.time() < end.time() else '' -%}
        {%- set be = '**_' if bs else '' %}
    {{ "%s | %s | %s"|format(bs~start.strftime("%d.%m.%y %H:%M")~bs, bs~end.strftime("%d.%m.%y %H:%M")~be,'*' if be else '') }}
      {%- endfor %}
    {% endif %}
    {% if plan and plan_name in ['use_time'] %}
      {%- set tarifs = ["High","Medium","Low","Other"] -%}
      {% for sea in plan|default({}) -%}
        {%- set unit = sea.unit|default('-') -%}
        {%- set wk = sea.weekday|default([]) -%}
        {%- set we = sea.weekend|default([]) -%}
        {%- set m_start = isnow.replace(month=(sea.sea|default({})).start_month|default(1)|int(1)) -%}
        {%- set m_end = isnow.replace(month=(sea.sea|default({})).end_month|default(12)|int(12)) -%}
        {%- set is_same = sea.is_same|default(true) %}
    {{ '**Season: '~[m_start.strftime("%b"),m_end.strftime("%b")]|join(' - ')~',   Weekends: '~('SAME' if is_same else 'DIFF')~'  ('~plan_name~')**' }}
    {{ "%s | %s | %s | %s | | %s | %s | %s | %s"|format('Start', 'End', 'Type', 'Price', 'Start', 'End', 'Type', 'Price') }}
    {{ ":---|:---|:---|---|---|:---|:---|:---|:---" }}
        {#- Show different weekend side by side in season -#}
        {% for idx in range(max(wk|length,we|length)) -%}
          {%- if wk|length > idx -%}
            {%- set tarif = wk[idx].type|default(0)|int(0) -%}
            {%- set price = sea.weekday_price | selectattr('type',"eq",tarif) | map(attribute='price') | list | first | float(0) -%}
            {%- set tarif = tarifs[tarif-1] if tarif is number and 0 < tarif <= tarifs|length else '------' -%}
            {%- set start = today_at(wk[idx].start_time|default(0)|string~":0") -%}
            {%- set end = wk[idx].end_time|default(0)|int(0) -%}
            {%- set end = today_at(end|string~":0") if end < 24 else today_at("0:0") + timedelta(days=1)  -%}
            {%- set bs = '_**' if m_start.month <= isnow.month <= m_end.month and isnow.weekday() in range(5) and start.time() <= isnow.time() < end.time() else '' -%}
            {%- set be = '**_' if bs else '' -%}
            {%- set row = "%s | %s | %s | %s%.2f %s | |"|format(bs~start.strftime("%H:%M")~be, bs~end.strftime("%H:%M")~be, bs~tarif~be, bs, price, unit~be~('*' if bs else '')) -%}
          {%- else -%}
            {%- set row = " | | | | | | " -%}
          {%- endif %}
          {%- if not is_same and we|length > idx -%}
            {%- set tarif = we[idx].type|default(0)|int(0) -%}
            {%- set price = sea.weekend_price | selectattr('type',"eq",tarif) | map(attribute='price') | list | first | float(0) -%}
            {%- set tarif = tarifs[tarif-1] if tarif is number and 0 < tarif <= tarifs|length else '------' -%}
            {%- set start = today_at(we[idx].start_time|default(0)|string~":0") -%}
            {%- set end = we[idx].end_time|default(0)|int(0) -%}
            {%- set end = today_at(end|string~":0") if end < 24 else today_at("0:0") + timedelta(days=1)  -%}
            {%- set bs = '_**' if m_start.month <= isnow.month <= m_end.month and isnow.weekday() in range(5,7) and start.time() <= isnow.time() < end.time() else '' -%}
            {%- set be = '**_' if bs else '' -%}
            {%- set row = row ~ "%s | %s | %s | %s%.2f %s"|format(bs~start.strftime("%H:%M")~be, bs~end.strftime("%H:%M")~be, bs~tarif~be, bs, price, unit~be~('*' if bs else '')) -%}
          {%- else -%}
            {%- set row = row ~ " | | | " %}
          {%- endif %}
    {{ row }}
        {%- endfor %}
      {% endfor %}
    {% endif %}
  {% endfor %}
  {% if not plan %}
    {{ "No schedule available"}}
  {% endif %}
```
</details>

**Notes:**
- Shared accounts have no access to the schedule
- Solarbank 2 has less settings per time slot than Solarbank 1, making it easier to adjust
- Solarbank 2 schedules can be created for individual weekdays. Each group of weekdays has its own plan ID. A weekday can only be configured into one plan ID
- The defined custom_rate_plan is only used when the usage mode is set to `manual` (custom usage) or `smartmeter` for the case of smart meter communication loss
- The defined blend_plan is only used when the usage mode is set to `smartplugs`
- The manual_backup plan is only used for the backup charge mode of AC models. It will overlay any other mode if enabled and in defined datetime interval.
- The use_time plan is only used when the Usage Time mode of AC models is enabled


## Script to manually modify appliance schedule for your solarbank

With Home Assistant 2024.3 you have the option to manually enter parameters for a script prior execution. This is a nice capability that let's you add an UI capability for an action right into your dashboard. You just need to create a script with input fields that will run the selected solarbank action using the entered parameters. Following is a screenshot of the more info dialog for the script entity:

![Change schedule script][schedule-script-img]

Below are example scripts which you can use for either Solarbank 1 or Solarbank 2 devices, you just need to replace the entity name in the action data entity_id field with your device sensor that represents the output preset and has the schedule attribute. If you have multiple systems, you can make the entity also a selectable field in the script similar to the action. For dual solarbank systems, you just need one of the 2 solarbank preset entities to apply the change, since the schedule is shared.

<details>
<summary><b>Expand to see script code</b><br><br></summary>

#### Script code to adjust Solarbank 1 schedules

```
alias: Change Solarbank 1 Schedule
fields:
  action:
    name: Action
    description: Choose which action to use
    required: true
    default: anker_solix.update_solarbank_schedule
    selector:
      select:
        mode: dropdown
        options:
          - label: Update schedule
            value: anker_solix.update_solarbank_schedule
          - label: Set schedule
            value: anker_solix.set_solarbank_schedule
  start_time:
    name: Start time
    description: Start time of the interval (seconds are ignored)
    required: true
    default: "00:00:00"
    selector:
      time: null
  end_time:
    name: End time
    description: >-
      End time of the interval (seconds are ignored). For 24:00 you must enter 23:59
    required: true
    default: "23:59:00"
    selector:
      time: null
  appliance_load:
    name: Appliance load preset
    description: Watt to be delivered to the house
    required: false
    default: 100
    selector:
      number:
        min: 100
        max: 1600
        step: 10
        unit_of_measurement: W
  device_load:
    name: Device load preset
    description: Watt to be delivered by the solarbank device
    required: false
    default: 50
    selector:
      number:
        min: 50
        max: 800
        step: 5
        unit_of_measurement: W
  allow_export:
    name: Allow export
    description: >-
      If deactivated, the battery is not discharged or, if an MI80 inverter or 0 W switch is installed, the charging priority is used without exporting to the house
    required: false
    selector:
      boolean: null
    default: false
  discharge_priority:
    name: Discharge priority
    description: >-
      If activated, battery discharge will be prioritized for export and possible PV production will be stopped
    required: false
    selector:
      boolean: null
    default: false
  charge_priority_limit:
    name: Limit for charge priority
    description: >-
      The charging priority is used up to the set charge level when the MI80 inverter is set. Setting is ignored if no 0 W switch is installed or no MI80 inverter is set.
    required: false
    default: 80
    selector:
      number:
        min: 0
        max: 100
        step: 5
        unit_of_measurement: "%"
sequence:
  - service: |
      {{action}}
    target:
      entity_id: sensor.solarbank_e1600_home_preset
    data:
      start_time: |
        {{start_time}}
      end_time: |
        {{end_time}}
      appliance_load: |
        {{appliance_load|default(None)}}
      device_load: |
        {{device_load|default(None)}}
      allow_export: |
        {{allow_export|default(None)}}
      discharge_priority: |
        {{discharge_priority|default(None)}}
      charge_priority_limit: |
        {{charge_priority_limit|default(None)}}
mode: single
icon: mdi:sun-clock
```

#### Script code to adjust Solarbank 2 schedules

```
alias: Change Solarbank 2 Schedule
fields:
  action:
    name: Action
    description: Choose which action to use
    required: true
    default: anker_solix.update_solarbank_schedule
    selector:
      select:
        mode: dropdown
        options:
          - label: Update schedule
            value: anker_solix.update_solarbank_schedule
          - label: Set schedule
            value: anker_solix.set_solarbank_schedule
  start_time:
    name: Start time
    description: Start time of the interval (seconds are ignored)
    required: true
    default: "00:00:00"
    selector:
      time: null
  end_time:
    name: End time
    description: >-
      End time of the interval (seconds are ignored). For 24:00 you must enter 23:59
    required: true
    default: "23:59:00"
    selector:
      time: null
  plan:
    name: Plan
    description: Plan to be modified (active plan is default)
    required: false
    selector:
      select:
        mode: list
        multiple: false
        translation_key: plan
        options:
          - custom_rate_plan
          - blend_plan
  week_days:
    name: Weekdays
    description: Weekdays for interval
    required: false
    selector:
      select:
        mode: list
        multiple: true
        translation_key: weekday
        options:
          - sun
          - mon
          - tue
          - wed
          - thu
          - fri
          - sat
  appliance_load:
    name: Appliance load preset
    description: Watt to be delivered to the house
    required: false
    default: 100
    selector:
      number:
        min: 0
        max: 800
        step: 10
        unit_of_measurement: W
sequence:
  - service: |
      {{action}}
    target:
      entity_id: sensor.solarbank_2_e1600_pro_home_preset
    data:
      start_time: |
        {{start_time}}
      end_time: |
        {{end_time}}
      plan: |
        {{plan|default(None)}}
      week_days: |
        {{week_days|default(None)}}
      appliance_load: |
        {{appliance_load|default(None)}}
mode: single
icon: mdi:sun-clock
```
</details>

In order to run the script interactively from the dashboard, you just need to add an actionable card and select the script as entity with the action to show the more-info dialog of the script. If you place the schedule markdown card on the left or right column of the dashboard, you can review the active schedule while entering the parameters for the changes you want to apply. That gives you similar schedule management capabilities as in the Anker App...Nice.

**Notes:**
- You may have to reload your browser window when the changed or inserted schedule intervals are not directly represented in the markdown card
- See further notes above for adjusting the appliance home load parameters or schedule when things are behaving differently than expected


## Other integration actions

### Get system info action

Starting with version 2.0.0, a new action was added for the system total yield entity in order to query the overall system information from the cloud Api, which contains the data that is presented on the Anker App home page screen. This data is used by the integration to represent most but not all of the entities. It may be helpful to debug what values are actually available on the Api cloud at the time requesting them. Following is an example screenshot showing only the top of the response:

![Get system info service][get-system-info-service-img]

Version 2.3.0 added an option to include cached data in the presented response, so additional fields as cached or merged by the Api library may be shown.

### Export systems action

Starting with version 2.1.2, a new action was added to simplify an anonymized export of known Api information available for the configured account. The Api responses will be saved in JSON files and the folder will be zipped in your Home Assistant `/config` folder under `www/community/anker_solix/exports`. The `www` folder is the local file folder for the HA dashboard to access files directly via the browser. It is also used by custom dashboard cards. Home Assistant automatically maps this folder to `/local` in the URL path.
The action response field `export_filename` will provide the zipped filename url path as response to the action. This allows easy download from your HA instance through your browser when navigating to that url path. Optionally you can download the zip file via Add Ons that provide file system access.

**Important:**
If the system export just created the `www` folder on your HA instance, it is not mapped yet to the `/local` folder and cannot be accessed through the browser. You have to restart your HA instance to have the new `www` folder mapped to `/local`.

**Notes:**
- This action will execute a couple of Api queries and run about 10 or more seconds. **If Api throttling is active, it may even run 1-3 minutes.**
- **The UI button will only show green once the action is finished.** An error will be raised if the action is retriggered while there is still a previous action active.
- There may be logged warnings and errors for queries that are not allowed or possible for the existing account. The resulting log notifications for the anker_solix integration can be cleared afterwards
- The url path that is returned in the response needs to be added to your HA server hostname url for direct download of the zipped file (the `www` filesystem folder is accessible as `/local` in the url navigation path as given in the response).


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/ha-anker-solix
[releases]: https://github.com/thomluther/ha-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/ha-anker-solix.svg?style=for-the-badge
[discussions]: https://github.com/thomluther/ha-anker-solix/discussions
[discussions-shield]: https://img.shields.io/github/discussions/thomluther/ha-anker-solix.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/badge/Licence-MIT-orange
[license]: https://github.com/thomluther/ha-anker-solix/blob/main/LICENSE
[python-shield]: https://img.shields.io/badge/Made%20with-Python-orange
[buy-me-coffee]: https://www.buymeacoffee.com/thomasluthe
[integration-img]: doc/integration.png
[config-img]: doc/configuration.png
[reconfigure-img]: doc/reconfigure.png
[options-img]: doc/options.png
[system-img]: doc/system.png
[inverter-img]: doc/inverter.png
[solarbank-img]: doc/solarbank.png
[connected-img]: doc/connected_devices.png
[notification-img]: doc/notification.png
[solarbank-dashboard-img]: doc/solarbank-dashboard.png
[solarbank-dashboard-light-img]: doc/solarbank-dashboard-light.png
[dual-solarbank-entities-img]:  doc/dual-solarbank-entities.png
[system-dashboard-img]: doc/system-dashboard.png
[schedule-markdown-img]: doc/schedule-markdown.png
[schedule-2-markdown-img]: doc/schedule-2-markdown.png
[schedule-script-img]: doc/change-schedule-script.png
[schedule-service-img]: doc/schedule-service.png
[request-schedule-img]: doc/request-schedule.png
[solarbank-2-system-dashboard-img]: doc/solarbank-2-system-dashboard.png
[solarbank-2-pro-device-img]: doc/Solarbank-2-pro-device.png
[solarbank-2-pro-diag-img]: doc/Solarbank-2-pro-diag.png
[smart-meter-device-img]: doc/Smart-Meter-device.png
[get-system-info-service-img]: doc/get-system-info-service.png

