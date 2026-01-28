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

> [!WARNING]
>  **The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library. Users must accept these conditions prior integration usage. A consent automatically includes future integration or Api library updates, which can extend the integration functionality for additional device settings or monitoring capabilities.** 🚨


# Table of contents

1. **[Disclaimer](#disclaimer)**
1. **[Usage terms and conditions](#usage-terms-and-conditions)**
1. **[Device structure used by the integration](#device-structure-used-by-the-integration)**
    * [Example screenshots](#example-screenshots)
1. **[Anker account limitation and usage recommendations](#anker-account-limitation-and-usage-recommendations)**
    * [Previous work around to overcome parallel usage restriction](#previous-work-around-to-overcome-parallel-usage-restriction-of-owner-account-no-longer-required-since-august-2025)
1. **[Data refresh configuration options](#data-refresh-configuration-options)**
    * [Option considerations for Solarbank 2 systems](#option-considerations-for-solarbank-2-systems)
    * [Default hub configuration options](#default-hub-configuration-options)
1. **[MQTT connection and integration](#mqtt-connection-and-integration)**
    * [Common MQTT options](#common-mqtt-options)
    * [Device specific MQTT options](#device-specific-mqtt-options)
    * [Device real time triggers](#device-real-time-triggers)
    * [Device status requests](#device-status-requests)
1. **[Switching between different Anker Power accounts](#switching-between-different-anker-power-accounts)**
1. **[How to create a second Anker Power account](#how-to-create-a-second-anker-power-account)**
1. **[Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting](#automation-to-send-and-clear-sticky-actionable-notifications-to-your-smart-phone-based-on-api-switch-setting)**
    * [Automation code for actionable notification](#automation-code-for-actionable-notification)
1. **[Customizable entities of the Api cache](#customizable-entities-of-the-api-cache)**
    * [Battery Capacity](#battery-capacity)
    * [Dynamic Price Provider selection](#dynamic-price-provider-selection)
    * [Dynamic price fee and VAT](#dynamic-price-fee-and-vat)
1. **[Modification of the appliance home load settings](#modification-of-the-appliance-home-load-settings)**
    * [Modification of Solarbank 2+ home load settings](#modification-of-solarbank-2-home-load-settings)
    * [Care must be taken when modifying Solarbank 1 home load settings](#care-must-be-taken-when-modifying-solarbank-1-home-load-settings)
    * [Pro tips for home load automation with Solarbank 1](#pro-tips-for-home-load-automation-with-solarbank-1)
    * [Home load automation considerations for Solarbank 2+](#home-load-automation-considerations-for-solarbank-2)
    * [How can you modify the home load and the solarbank schedule](#how-can-you-modify-the-home-load-and-the-solarbank-schedule)
        - [1. Direct parameter changes via entity modifications](#1-direct-parameter-changes-via-entity-modifications)
        - [2. Solarbank schedule modifications via actions](#2-solarbank-schedule-modifications-via-actions)
        - [3. Interactive solarbank schedule modification via a parameterized script](#3-interactive-solarbank-schedule-modification-via-a-parameterized-script)
    * [Schedule action details and limitations](#schedule-action-details-and-limitations)
1. **[Modification of Solarbank AC settings](#modification-of-solarbank-ac-settings)**
    * [Manual backup charge Option](#manual-backup-charge-option)
        - [Backup charge option control by entities](#backup-charge-option-control-by-entities)
        - [Modify AC backup charge action](#modify-ac-backup-charge-action)
    * [Time of Use mode](#time-of-use-mode)
        - [Time of Use plan control by entities](#time-of-use-plan-control-by-entities)
        - [Modify Time of Use plan action](#modify-time-of-use-plan-action)
        - [Usage of flexible tariffs with the Time of Use mode](#usage-of-flexible-tariffs-with-the-time-of-use-mode)
1. **[Modification of Solarbank 3 settings](#modification-of-solarbank-3-settings)**
    * [Smart mode](#smart-mode)
        - [Usage of Smart mode](#usage-of-smart-mode)
    * [Time Slot mode](#time-slot-mode)
        - [Usage of dynamic tariffs with the Time Slot mode](#usage-of-dynamic-tariffs-with-the-time-slot-mode)
1. **[Toggling system price type or currency settings](#toggling-system-price-type-or-currency-settings)**
    * [Dynamic utility rate plans options](#dynamic-utility-rate-plans-options)
        - [Dynamic price provider](#dynamic-price-provider)
        - [Dynamic price fees and taxes](#dynamic-price-fees-and-taxes)
        - [Export tariff options](#export-tariff-options)
1. **[Solar forecast data](#solar-forecast-data)**
1. **[Modification of vehicles](#modification-of-vehicles)**
1. **[Markdown card to show the defined Solarbank schedule](#markdown-card-to-show-the-defined-solarbank-schedule)**
    * [Markdown card for Solarbank 1 schedules](#markdown-card-for-solarbank-1-schedules)
    * [Markdown card for Solarbank 2+ schedules](#markdown-card-for-solarbank-2-schedules)
1. **[Apex chart card to show your forecast data](#apex-chart-card-to-show-forecast-data)**
1. **[Script to manually modify appliance schedule for your solarbank](#script-to-manually-modify-appliance-schedule-for-your-solarbank)**
    * [Script code to adjust Solarbank 1 schedules](#script-code-to-adjust-solarbank-1-schedules)
    * [Script code to adjust Solarbank 2+ schedules](#script-code-to-adjust-solarbank-2-schedules)
    * [Script code to adjust Solarbank AC backup charge](#script-code-to-adjust-solarbank-ac-backup-charge)
    * [Script code to adjust Solarbank AC Time of Use plan](#script-code-to-adjust-solarbank-ac-time-of-use-plan)
1. **[Other integration actions](#other-integration-actions)**
    * [Export systems action](#export-systems-action)
    * [Get system info action](#get-system-info-action)
    * [Get device info action](#get-device-info-action)
    * [Api request action](#api-request-action)
        - [Hints and tips when using Api requests](#hints-and-tips-when-using-api-requests)
        - [Format of the payload](#format-of-the-payload)
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
Starting with version 2.3.0, the integration will also create one `account` device for each hub configuration. The `account` device has assigned all `system` devices and stand alone End Devices of your Anker account as well as common Api entities that belongs to the user/account.

### Example screenshots

Following are anonymized examples how the Anker power devices will be presented (Screenshots are from initial release without changeable entities):

#### System Device with Solarbank E1600 and MI80 inverter

![System Device][system-img]
![Connected Devices][connected-img]

#### Solarbank E1600 Device

![Solarbank Device][solarbank-img]

#### MI80 Inverter Device

![Inverter Device][inverter-img]

Following are screenshots from basic dashboard cards including sensors and most of the changeable entities that are available when using the system main account:

#### Dark Theme examples of Solarbank 2 E1600 Pro with Smart Meter

![System Dashboard][solarbank-2-system-dashboard-img]

#### Light Theme examples of Solarbank E1600**

![Solarbank Dashboard Light Theme][solarbank-dashboard-light-img]

Screenshots from other device types when using the system main account:

#### Additional device preset entities only available in supported dual Solarbank E1600 systems**

![Dual Solarbank Entities][dual-solarbank-entities-img]

#### Solarbank 2 E1600 Pro device**

![Solarbank 2 Pro Device][solarbank-2-pro-device-img]  ![Solarbank 2 Pro Device Diag][solarbank-2-pro-diag-img]

#### Smart Meter device**

![Smart Meter Device][smart-meter-device-img]

#### Power Dock device**

![Power Dock Device][power-dock-device-img]

#### Vehicle device**

![Vehicle Device][vehicle-device-img]


> [!NOTE]
> When using a shared system account for the integration, device detail information is limited and changes are not permitted. Therefore shared system account users may get presented no control entities and only a subset of entities by the integration.

> [!TIP]
> Using the main account and enabling the [optional MQTT server connection]((#mqtt-connection-and-integration)), you may get additional devices, entities and device controls which are only available through the MQTT server connection.


## Anker account limitation and usage recommendations

Prior August 2025, usage of the same Anker account in the integration and the Anker mobile app at the same time was not possible due to security reasons enforced by Anker. Therefore, it was recommended to create a second account and use one in the integration and the other one in the mobile app. For instructions to create a second account and share the system, see [How to create a second Anker Power account](#how-to-create-a-second-anker-power-account).
**This Anker account usage limitation was relaxed end of June 2025** and a second account for integration usage is no longer mandatory. For more details refer to the [Anker Account information in the README](README.md#anker-account-information).

Following is the integration configuration dialog:

![configuration][config-img]

> [!IMPORTANT]
> System members cannot manage any devices of the shared system or view any of their details. You can only see the system overview in the app. Likewise it is the same behavior when using the Api: You cannot query device details with the shared account because you don't have the required permissions for this data. However, a shared account is sufficient to monitor the overview values through the integration without being restricted for using the main account in the Anker app to manage your device settings if needed.

If you configure multiple integration hubs, it is important that NO devices are shared across those hub accounts. All integration entities and devices are generated with the device serials or site IDs as part of their unique ID, which is registered within HA. Sharing devices will therefore cause HA errors because of entity creation with non unique IDs while the configuration entry is being loaded. The integration will check and deny creating another hub that shares devices with an existing hub with a corresponding error. However, if the hubs were created before the system or device sharing was configured through the mobile App, one of the hubs will fail to (re-) load. Starting with version 3.4.0, a repair issue will be created to make this problem visible in the HA frontend.

![Repair issue][repair-issue-img]

You cannot repair the issue automatically, you can only ignore it. The repair issue will be deleted again once you resolved the device sharing across the configured hubs as reported in the issue, and all remaining integration hubs are (re-) loaded successfully. The simplest solution will be to delete one of the two hubs sharing the devices.

### Previous work around to overcome parallel usage restriction of owner account (NO longer required since August 2025)

A work around to overcome the previous account usage limitation had been implemented via an Api switch in the `account` device. When disabled, the integration stops any Api communication for the account configured in the hub entry. During that time, you could use the same account again for login through the Anker app and regain full control to modify device settings or perform firmware upgrades as needed. Afterwards, you could re-activate Api communication in the integration again, which automatically logged in the integration client to continue reporting data for that account. While the Api switch is off, all sensors related to this Anker account (hub entry) will become unavailable to avoid reporting of stale data.

To simplify usage of this workaround, please see [Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting](#automation-to-send-and-clear-sticky-actionable-notifications-to-your-smart-phone-based-on-api-switch-setting) for an example automation, which sends a sticky mobile notification when the Api switch was disabled, using actionable buttons to launch the Anker App directly from the notification. It provides also actionable buttons to re-enable the switch again and clear the sticky notification. This avoids forgetting to re-enable your data collection once you are finished with your tasks in the Anker mobile app.


## Data refresh configuration options

The data in the cloud which can be retrieved via the Api is typically refreshed only once per minute at most. Most of the device types refresh cloud data only in 5 minute intervals. Therefore, it is recommended to leave the integration refresh interval set to the default minimum of 60 seconds, or increase it even further if no frequent updates are required. Refresh intervals are configurable from 30-600 seconds, but **less than 60 seconds will not provide more actual data and just cause unnecessary Api traffic.** Version 1.1.0 of the integration introduced a new system sensor showing the timestamp of the delivered Solarbank data to the cloud, which can help you to understand the age of the received data.

> [!NOTE]
> The solarbank seems to be the only Anker system device category that provides valid timestamp data (inverter or power panel data timestamps are not updated by the cloud).

During each Api refresh interval, the power sensor values of the systems and their devices will be refreshed, along with the actual system configuration and available end devices. There are more end device details available showing their actual settings, like power cut-off, auto-upgrade, schedule, system energy statistics etc. However, those details require much more Api queries and therefore are refreshed less frequently. The device details refresh interval can be configured as a multiplier of the normal data refresh interval. With the default options of the configured account, the device details refresh will run every 10 minutes, which is typically by far sufficient. If a device details update is required on demand, each end device has a button that can be used for such a one-time refresh. However, the button will re-trigger the device details refresh only when the last refresh was more than 60 seconds ago and there is no device refresh ongoing to avoid unnecessary Api traffic.

To prevent too many requests in a short amount of time, a configurable request delay was introduced with version 1.1.1. This may be adjusted to avoid too many requests per second and potentially overload the Api or keep it busy.

The default request timeout was reduced from 30 seconds to 10 seconds in version 3.3.0, since a single retry was implemented upon timeout or http errors which may indicate a temporary issue. Since version 3.3.1, you can also configure the request timeout between 5-60 seconds. Typically the Anker cloud servers responds in less than a second once the request could be submitted, and the default timeout of 10 seconds is sufficient. But there are also DNS timeout errors seen from various people which may depend on local or wide area network routing capabilities, which may sometimes require longer timeouts.

The cloud Api also enforces a request limit. This request limit is applied by the cloud and is independent of the used account. It is enforced per IP address and endpoint within the last ~minute. Originally this limit was ~25 requests for most endpoints. As of Feb. 2025, this endpoint limit was significantly reduced by Anker to 10-12 requests per IP and minute for frequently used endpoints. Every Api client you use in your home behind the same router IP will count towards that cloud limit, like running Anker Solix HA integration clients, Anker mobile app devices etc. The mobile App may appear only unresponsive or not showing data or charts when the endpoint limit is temporarily exceeded, but in the HA integration logs you will see errors as following:
```text
2025-02-28 16:54:34.343 ERROR (MainThread) [custom_components.anker_solix] Api Request Error: 429, message='Too Many Requests', url='https://ankerpower-api-eu.anker.com/power_service/v1/site/energy_analysis'
2025-02-28 16:54:34.344 ERROR (MainThread) [custom_components.anker_solix] Response Text: {"error_msg":"Request too soon. Your actions have been recorded."}
```
If those errors occur during setup or reload of the configuration entry, you may see your configuration entry flagged with error `429: Too many requests`. Upon such errors, some or all entities may become unknown, unavailable or show stale data until further Api requests are permitted. To avoid hitting the request limit, starting with release 2.5.5 a new endpoint throttling capability was implemented to the Api client session. A default endpoint limit of 10 will be used for the throttle, which can be adjusted as required. With release 2.5.7 the throttling is no longer activate for each endpoint, but activated only upon first `429: Too many requests` error. This avoids throttling loops for endpoints that may have a higher limit. Setting the endpoint limit to 0 will disable and reset the active throttling and provide the former client session behavior.

> [!NOTE]
> In order to avoid that potential endpoint throttling loops occurs during (re)load of the configuration or re-activation of the Api refresh switch, while doing the initial data poll for entity creation, the initial poll of energy details is now deferred to the next data refresh cycle. This ensures fast configuration (re)loads and avoids that this process may be elongated for minute(s). This change however has the disadvantage, that energy entity creation will be delayed by one or more minutes. **So be calm and allow the integration a few minutes after restart or Api refresh re-activation to poll initial energy data and create or reactivate the corresponding entities.**

> [!IMPORTANT]
> The endpoint limit throttle is applied only for a single Api session. Other Api clients may query the same endpoints within same minute and therefore the integration may still exceed the endpoint limit. If you create multiple Anker configuration hub entries, you need to distribute the allowed endpoint limit (10) accordingly across all hub entries since their Api requests can run in parallel. Another client like your Anker app using another account will contribute to the limit as well if that is connected to the cloud through your same router IP address.

Due to the enforced Anker Cloud Api endpoint limit, it is recommended to exclude the energy categories from your hub configuration entry if you want to avoid such request errors or the throttling delays, which aim to avoid exceeding the endpoint limit for larger or multiple systems configurations. The daily energy entities require by far the most queries to the same endpoint, and therefore may cause one or more minute throttle delays for data refreshes even in small system configurations.
Furthermore, all energy statistic entities are excluded from new configuration entries per default. They may increase the required Api requests significantly as shown in the discussion post [Api request overview](https://github.com/thomluther/ha-anker-solix/discussions/32). Desired energy statistics can be re-enabled by removing them from the exclusion list in the configuration options.

Furthermore there may be request errors when you configured more than one Anker hub (or use the Anker app in parallel) in case multiple Api requests are done in parallel from same IP address, even if that is for different accounts or systems. This is typically logged with error code 21105 as shown in following example:
```text
[custom_components.anker_solix] (21105) Anker Api Error: Failed to request. 2024-09-26 08:59:39.442 ERROR (MainThread) [custom_components.anker_solix] Response Text: {"code":21105,"msg":"Failed to request.","trace_id":"<trace_id>"}
```
Request errors may cause entities to become unavailable, or even cause the configuration (re)load to fail. You cannot avoid parallel requests of multiple clients by changing the hub configuration options. Starting with release 2.5.5, some enhancements have been implemented to better tolerate multiple hub configuration entries and parallel request errors:
  * Added a request retry capability to the Api client session for return codes that can be classified as 'Api busy error', such as code 21105. A single retry will be attempted for the request after a random delay of 2-5 seconds, which should mask parallel request errors in most cases. A warning will be logged for the retry attempt to allow monitoring for their frequency.
  * If more than one Anker hub configuration entry is created, the integration will try to stagger their individual data refresh polls:
      - The regular refresh interval may be delayed by 5 or more seconds to allow other active client refreshes to complete.
      - The device details refresh may be delayed by at least 2 minutes to allow other active or delayed device refreshes to complete, assuming they can run into 1-2 throttle delays. Warnings will be logged for any refresh that is being delayed.

All the above enhancements should better tolerate multiple hub configuration entries and avoid that your entities become unavailable temporarily.

With release 2.6.0 there have been added diagnostic entities to the account device to show the last refresh timestamp as well as the duration in the attributes.
Those entities however are disabled by default and must be enabled if you want more insights on the integration refresh intervals and runtimes. They may help to recognize throttling loops or interval staggering according to their update history.
![Api refresh sensors][api-refresh-sensors-img]![Api refresh history][api-refresh-history-img]

The configuration workflow was completely reworked since version 1.2.0. Configuration options can now already be modified right after successful account authorization and before the first data collection is done. Excluded device types, details categories or energy statistics can be reviewed and changed as needed prior the initial data poll. Device types of no interest can be excluded completely. Exclusion of energy categories and specific system or solarbank categories may help to further reduce the number of required Api requests and customize the presented entities of the integration.

### Option considerations for Solarbank 2 systems

Anker changed the device data publish intervals with Solarbank 2 power systems. While Solarbank 1 devices publish their MQTT data every 60 seconds to the Api cloud, Solarbank 2 systems seem to use different intervals for MQTT data publishing:
   - Default interval is **~5 minutes**: After ~60 seconds, the cloud considered the last values obsolete at initial product release. That resulted in no longer returning valid values upon refresh requests (only 0 values), until new MQTT data has been received again from the devices. There was a change implemented in the cloud around 25. July 2024 to provide always the last known data upon Api refresh requests. This eliminated the missing value problem for shared accounts in the Anker mobile app or 0 values in any api client responses.
   - Triggered interval is **~3 seconds**: When the mobile app is used with the main account, it triggers real time MQTT publish for applicable and owned devices which will permanently refresh also the Api cloud data. The same method is used for triggering live data updates of individual devices when watching device real time data. That means while watching the Solarbank 2 power system overview via main account in the anker app, you receive very frequent data updates from the cloud Api. Of course, this real time trigger is only applied while the home screen is watched to limit cloud Api requests, data traffic and device power consumption for the remaining times. Once the real time publish trigger times out after 5 minutes, the device falls back to its default publish interval.

In consequence, before the cloud change in July 2024, the HA integration typically received 1 response with valid data and another 4 responses with invalid data when using the default refresh interval of 60 seconds. **There is nothing the integration or the underlying Api library can do to trigger more frequent cloud data updates for Solarbank 2 systems**. Per default, the HA integration switched all relevant entities to unavailable while invalid data is returned. Optionally, you can change your integration configuration options to **Skip invalid data responses**, which will maintain the previous entity value until valid data is received again. While this means your entities will not become unavailable most of the time, they may present obsolete/stale data without your awareness. It is your choice how entities should reflect data that are marked invalid in the Api response, but neither of the options makes the data more current or reliable. The SB data time entity in the system device will reflect when the last data was provided by the Solarbank 2, or when the last valid data was read through the Api, since also that timestamp in the response is not always valid even if the data itself is valid. A new [action was implemented to get query system information](#get-system-info-action) that provides you a manual verification capability of available system data and power values in the cloud. Following [Anker article contains more information why data for Solarbank 2 may be inaccurate](https://support.ankersolix.com/de/s/article/Warum-ist-die-Datenanzeige-der-Solarbank-2-E1600-Pro-Plus-ungenau) (DE).

> [!NOTE]
> The cloud change in July 2024 did not change the cloud data update frequency for Solarbank 2 systems. It only avoids that the cloud considers older device data as obsolete, but always responds with last known data instead. It has the same effect as the new 'Skip invalid data responses' option that was implemented to the integration.

### Default hub configuration options

Starting with version 3.4.0 and introduction of new MQTT options, the hub options have been restructured and previous configurations have been migrated to the new structure. The default option view presents collapsed sections for Api and MQTT options and only the Exclusion categories are visible in the main option section. Per default, all energy categories are excluded since they may drive lots of additional Api queries during the less frequent device details poll and run into Api throttling for the energy statistics endpoint. You need to remove them from the exclusion if you want to see daily energies in your system for related device types.

![Options][options-img]

> [!IMPORTANT]
> The listed categories in the options panel are **EXCLUDED**. Categories in the 'Excludable dropdown list' are **INCLUDED**. The display of the excluded categories above the dropdown may be misleading, but that is managed by HA core and cannot be changed by the integration.

> [!NOTE]
> A change in the hub options that added more exclusions or disables the MQTT connection will completely remove the affected devices and re-register them with remaining entities as necessary. This avoids manual cleanup in HA of entities no longer provided by the integration. It has the disadvantage however, that customized entity deactivation or activation maybe has to be re-applied because re-registration will typically create the entities with their integration defined default activation setting.

The Api options as explained in [Data refresh configuration options](#data-refresh-configuration-options) come with following default settings:

![Api Options][options-api-img]

The MQTT options as explained in [MQTT connection and integration](#mqtt-connection-and-integration) come with following default settings:

![MQTT Options][options-mqtt-img]


## MQTT connection and integration

Since version 3.4.0, the integration implemented hybrid support of MQTT data beside cloud Api data. Version 3.5.0 added support for MQTT based device control entities. The MQTT server connection is optional and can be enabled in your hub configuration options. With usage of the MQTT server connection, all eligible and owned devices of your Anker account are subscribed for MQTT messages from the Anker cloud MQTT server. That means, the integration can receive any MQTT message published from those devices to the MQTT server. But the connection can also be used to publish MQTT commands from the integration to the MQTT cloud server, which are subscribed by your devices to allow their remote control. The cloud MQTT server connection gives the integration the same capabilities that the Anker mobile app provides to monitor and manage devices remotely via the MQTT connection.

However, since MQTT messages and commands are encoded and may differ for each device model, they have to be decoded and described first before your specific device model can be supported. For already described device models and message types, you may see additional device entities being created by the integration, or existing entities may get additional attributes. While additional attributes will immediately appear during a state update, additional entities are only created during the Api update interval in case new devices or entities are being discovered. So you have to expect that MQTT entities will be created with a delay of at least 1 minute.
Devices also publish different types of MQTT messages at different intervals and the MQTT data delivery has a 'Push' characteristic compared to the 'Pull' characteristic of cloud Api data. MQTT based entities and attributes are updated immediately as published device MQTT messages with corresponding data are received by the integration. Since many MQTT messages can be published in a short amount of time by multiple devices in your account, the integration delays the centralized states update by 2 seconds. This allows data consolidation of multiple messages in short time frames and limits the HA workload for processing state updates of all hub entities. That means in case of real time messages published by an active device real time data trigger, you can follow the updates in HA immediately with a maximum delay of 2 seconds.

> [!NOTE]
> MQTT based entities or attributes may appear only after a certain delay of one or more minutes after the MQTT server connection was started or the integration hub configuration was (re-) loaded. If the entities were existing previously, they may appear 'unavailable' until their MQTT data has been published and received again. Specific MQTT data may even require to activate the device real time data trigger, and affected entities may remain 'unavailable' or become stale if no real time trigger is active for the device. This heavily depends on which regular messages are sent by the device and whether they have a regular message publish interval at all. Some devices may send MQTT messages only once requested per command or real time trigger.

There are different types of MQTT messages, reported at different intervals and with different content. Not every created entity will be updated with each message. Furthermore, there are also special messages which are only sent if the device is triggered to publish real time data. These are typically sent in 3-5 second intervals, but only while the real time trigger is active for the device. If the device provides standard MQTT messages without trigger, they are typically sent in 60-300 seconds intervals, but some types are also sent irregularly upon changes, like network signal messages if provided by the device. Standard messages may contain the same, different or a subset of data contained in real time data messages. This varies per device model. Be aware that data delivery to the integration heavily depends on the state and accuracy of the MQTT message decoding and description in the [Api library](https://github.com/thomluther/anker-solix-api). If there is an incorrect value description, the value representation in the integration may be wrong! But this problem cannot be fixed by the integration or library maintainer. For problem analysis, you need to make familiar with the Api library and the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) to verify live messages sent by your owned device and see how the value decoding is actually described and how it must be changed or fixed to utilize the correct message fields or value conversions for your device model.

> [!IMPORTANT]
> MQTT data is supported only for devices owned by the used Anker account. If you are using a shared account without owned devices in the integration, you will have NO benefit from enabling the MQTT connection.

In order to recognize which entities may provide additional MQTT data, their attribution has been classified accordingly. Entities without MQTT attribution will only be updated by Api data. You can find the entities that benefit from MQTT data in the states panel of your HA developer tools. Filter for all entities that contain 'Anker Solix' in the attributes, some of them will show attribution of 'Api + MQTT'. Following example shows the battery health % that may be provided through MQTT data and you can find it in the attributes of battery state_of_charge entities.

![Entity attributes][entity-attributes-img]

> [!TIP]
> If you don't find any useful new data for your owned devices although you enabled the MQTT connection, your device model still has to be decoded and described. You can contribute by starting with the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) from the [Api library](https://github.com/thomluther/anker-solix-api) and follow the [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222). In order to decode MQTT commands of your device, please follow this [MQTT command and state analysis and description](https://github.com/thomluther/anker-solix-api/discussions/222#discussioncomment-14660599).

### Common MQTT options

Once you enable the MQTT server option in the hub configuration, you can find a new MQTT connection entity under your account device, which shows you the actual state of the MQTT server connection. Once the MQTT server is (re-) connected, all eligible MQTT devices are automatically subscribed and the integration can receive all MQTT messages which they publish to the server.

![Account MQTT entities][account-mqtt-entities-img]

Once devices are triggered for real time data, they can publish lots of messages and data, especially if you trigger them continuously. In order to keep track about the MQTT message traffic, an MQTT statistics entity is being provided, but that entity is disabled by default like other Api statistic entities. If you want to keep track and have more insight on the additionally produced MQTT traffic, you can enable this entity in your account device. It will show you the average MQTT data rate per hour, but also some other metrics like the MQTT session start time and a breakdown of which message types have been received per device model.

![MQTT statistics][mqtt-statistics-img]

For more details on message types and their content per device model, you have to consult the SOLIXMQTTMAP description in the [mqttmap.py](https://github.com/thomluther/ha-anker-solix/blob/main/custom_components/anker_solix/solixapi/mqttmap.py) module.

### Device specific MQTT options

Once you enable the MQTT server connection in the hub configuration, you will get a diagnostic [Real Time trigger](#device-real-time-triggers) button and a [Status Request](#device-status-requests) button for each device supporting MQTT. With those buttons you can control how the device publishes its status messages. The buttons can be used on demand or via an action in your HA automation.
Once first MQTT data has been received and extracted for your device, you will also get another diagnostic switch entity that allows you to configure how MQTT data should be merged with existing Api data for your device. The default setting is that Api data will be used preferably for any state or attribute data that exists in both, the Api and MQTT cache. If you prefer to overlay Api data with MQTT data, you can enable the MQTT overlay switch. The switch is a customized entity and the state is stored in the integration Api cache. Since the switch is declared as restore entity, the overlay setting per device should remain persistent across hub option changes or HA restarts which trigger a reload of the caches, and the last switch state should be restored once the switch is re-created.
The default MQTT overlay setting is Off, to prioritize display of Api values if a corresponding value may be provided also in the MQTT data (classical behavior).

> [!NOTE]
> The MQTT overlay setting has no effect on data that is being provided only via Api or MQTT messages. It just defines how you want to merge data that is being provided by both interfaces at different points in time.

While an MQTT overlay may have the benefit of providing most current data for your device, it may scramble the holistic data view for your device (or system), since only a subset of entities or attributes are really refreshed at a given point in time. Some data may even be generated or calculated only by the cloud and cannot be updated at all with MQTT data updates. Another disadvantage is that wrong decoding descriptions for your device type or wrong data merge definitions could scramble valid Api data of the entity. You can see the overlay effect immediately by toggling the switch while you verify your device entity states during toggling.

If you want to maintain a holistic data view, the MQTT overlay should remain disabled. Also with Api data preference you can benefit from real time data triggers or status requests, since the cloud servers receive the same device messages for their recording backend, and the regular Api data polls may then receive more frequent holistic data updates during the normal Api refresh cycles.

> [!IMPORTANT]
> The Api refresh cycle can be configured in the hub options, the minimum however remains at 30 seconds. Upon reduction of your default Api refresh interval, you should consider increasing the details refresh multiplier accordingly, since that is just a multiplier for the refresh interval and drives lots of Api queries that provide data which are not changed frequently. See [API data refresh configuration options](#data-refresh-configuration-options) for more details.

At the end, you have to test the best overlay setting for each of your Anker Solix devices according to your preferences. Therefore the MQTT overlay is customizable per device. However, be aware that future integration or Api library updates may change how individual entity values appear or are merged with an active MQTT overlay. So the data appearance behavior for your specific device may change with new integration versions.

Once MQTT data is available for a device, there will also be a diagnostic sensor that shows the timestamp of last MQTT data reception. It does not mean that all MQTT based data has been updated at that point in time. Rather it means that any of the device data has an extracted value from last message, which however depends on the received message type. Nevertheless, you can use the timestamp as indicator when the **last** MQTT data was extracted for your device. Furthermore, frequent timestamp updates in 3-5 second intervals will indicate that the device is sending real time messages which are being received. Optionally you can use it to verify if the device sends an immediate status once you press the status request button.

Following is an example of the diagnostic device entities available once MQTT data has been received:

![Device MQTT diagnostic entities][device-mqtt-diag-entities-img]

### Device real time triggers

The integration supports a diagnostic button per MQTT managed device that can be used to trigger real time data status messages of the device. The timeout used for the real time publish duration can be configured in the MQTT options of your hub. If the device will receive other real time triggers from the mobile App, the timeout used in the last trigger command will be applied by the device. The app typically uses timeouts of 300 seconds, which is also the default timeout in the [MQTT options of the hub configuration](#default-options-as-of-version-340).

Depending on how devices publish their data in regular messages, you may need the real time trigger only to get more frequent data updates. However, data which is only available in real time messages will get stale, if the real time data publish period will timeout. The integration provides the trigger button for each eligible device and you can control it according to your customized needs via an automation that will press the button at regular intervals or only under certain conditions, which you can define in your automation.

> [!IMPORTANT]
> Be aware that real time data may come with a cost if triggered permanently:
> - There will be larger amounts of traffic to your HA server but also between the devices and the Anker MQTT and Cloud servers
> - The Anker cloud infrastructure may not be scalable enough to maintain such 24x7 real time traffic for growing number of devices, since that is no use case with normal mobile App usage
> - The devices may be kept awake and never go to sleep mode, therefore using more power than necessary
> For those reasons, the trigger is only a button that satisfies the MQTT real time data trigger command and it will not be provided as permanent switch control. I would not recommend permanent trigger usage either, unless you have no other choice to receive desired device data.

> [!NOTE]
> Anker has various implementations of the real time trigger capability depending on the device type. While newer devices seem to repeat the message publish cycles by themselves, older device types like the Solarbank 1 seem to get triggered by the cloud with regular status requests to the device. That means the cloud may driving the real time trigger functionality for the timeout duration. However, it was also identified, that the cloud driven real time trigger depends on the actual device state. So there is no guarantee, that you get regular real time data from such devices upon a real time trigger command. However, those devices may fully support the [MQTT status request](#device-status-requests) command, which should be automated preferably at your customized automation trigger interval.


### Device status requests

Integration version 3.4.1 added another diagnostic button for a single MQTT status request of the device. If fully supported by the device, it will publish one set of status message(s) that are otherwise only sent if the real time trigger is active. However, devices may also send only the main status message without optional extra status messages, which may be provided only if the real time trigger is active.

> [!NOTE]
> Anker has no consistent implementation across their Solix devices whether they publish all status messages upon a single status request. Especially Solarbank 2 and later, as well as Multisystem constellations have many extra status messages that are only published while the **real time trigger** is active. These are messages with expansion battery details, or messages that consolidate actual states from all coupled devices with the overall data values.

Depending on which message(s) the various devices publish upon a status request, you may see that some of your MQTT based entity states will not refresh. However, if all relevant entities are being refreshed with a status request, that should be the preferred button for any of your customized automation, since you have more control about the extra MQTT data traffic. For example, if you need to get state updates only every 30 or 15 seconds, you can control that with the status request button and the frequency when and how often your automation triggers. The real time trigger button instead does not allow to control the message traffic or frequency.


## Switching between different Anker Power accounts

The integration will setup the entities with unique IDs based on device serials or a combination of serial numbers. This makes them truly unique and provides the advantage that the same entities can be re-used after switching the integration configuration to another shared account. While the entity history is not lost, it implies that you cannot configure different accounts at the same time **once they share a system**. Otherwise, it would cause HA setup errors because of non unique entities. Therefore, new integration hub configurations are validated and not allowed if they share systems or devices with an active hub configuration.
Up to release 2.1.0, if you wanted to switch between your main and shared account, you had to delete first the active configuration and then create a new configuration with the other account. While the devices and entities for the configured account will be created, deleted entities will be re-activated if their data is accessible via Api for the configured account. That means if you switch from your main account to the shared account, only a subset of entities will be re-activated. The other deleted entities and their history data may remain available until your configured HA recorder interval is over. The default HA recorder history interval is 10 days.

Starting with HA 2024.04, there is a new option to 'Reconfigure' an active integration hub configuration. This integration reconfiguration capability has been implemented with integration version 2.1.0 and allows a simplified, direct account reconfiguration from the integration's menu as shown in following example:
![Reconfigure][reconfigure-img]

> [!NOTE]
> While changing your active configuration to another account, the same actions and validations will be performed in background as via configuration entry deletion and re-creation. Using another account that shares any system or device with any active hub configuration except the modified one is not allowed. Once the configuration change is confirmed for the new or same account, all devices and entities will be unregistered and therefore removed, and afterwards recreated to adjust for the manageable entities of that modified account. Confirming a reconfiguration to the same account can therefore be used as workaround to clear orphaned entities. Those can occur when you recreate or reconfigure your power systems in the Anker app or change alias names for existing devices, since that alias name is used for automated entity_id generation.


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

Make sure to replace following entities used in the example below with your own entities:
- `switch.accountalias_country_api_usage` (This is your integration hub switch for the api usage, the entity is part of the 'account' device of the integration devices)
- `notify.my_smartphone` (This is your mobile notification entity, you can find your notify entities in the developer tab or your HA entities panel)

The system variable is automatically generated based on the device name of the entity that triggered the state change.

> [!NOTE]
> If you want to modify the notification to work with your iPhone, please refer to the [HA companion App documentation](https://companion.home-assistant.io/docs/notifications/notifications-basic/) for IOS capabilities.

### Automation code for actionable notification

<details>
<summary>Expand to see automation code</summary>

```yaml
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


## Customizable entities of the Api cache

The cloud Api does not provide all data that you may see in the Anker mobile app. Some data, especially device data, is available only via the cloud MQTT server, for which no interface exists. Some useful data may also not be provided at all by Anker, like battery capacity or remaining battery energy. Integration version 3.0.0 started to support the Api cache customization feature that was introduced into the Api library. This feature added the capability to customize certain values in the Api cache without that they require or replace corresponding real values provided via the cloud. If the user provides a customized value for a field, this data can either be used preferably by virtual fields (assumed or calculated fields), or alternatively if expected cloud data fields cannot be obtained or identified.
However, customization of Api cache data alone does not provide much benefit. Any customization will be lost upon every restart of the Api session, since the cache is rebuild from scratch each time. Therefore this version also added an optional restore capability for entities that have been declared as customizable. Restore entities will save last state and extra entity information upon HA restarts or integration reload and reconfiguration. The restore data is also saved regularly by HA in 15 minute intervals. Such a restored state can then be used to re-apply any entity customization to the Api cache and avoid that your customizations are being lost or forgotten across restarts.

Following entities are utilizing the Api cache customization capabilities and now provide better integration usage.

### Battery Capacity:

This number entity allows you to adjust the installed capacity of your device in case the calculated capacity is wrong (for example the intermix of Solarbank 2 and 3 battery expansions with different capacity that cannot be determined via the Api). You can also adjust the battery capacity for lifetime degradation, which will reduce the usable capacity over the years. The customized capacity value is used in preference to the calculated capacity to evaluate the theoretical battery energy that can be discharged: `SOC * Capacity`. Therefore you can now easily use this entity as well to adjust the calculated battery energy and make it more accurate to the DC or even AC energy that you can measurably discharge to your home in the evening. The entity also tracks the calculated capacity in the attributes. Whenever the calculated capacity is changed during restore, it is considered as change in the installation and the entity is reset to the calculated value. That means if you expand your solarbank, or modify your installation for the winter season, you may need to adjust the battery capacity entity again if the calculated value is wrong.

### Dynamic Price Provider selection:

The provider is required to query the correct spot prices through the cloud Api. Those spot prices can also be queried independently of your actual system type and are provided for up to 35 hours in advance. The configured provider for your system however can only be queried and changed when using the owner account with the integration. Whenever the provider was found or set once for your Solarbank 3 system, it will be customized in Api cache and used as alternate data if not available through the active member account. The provider restore and cache customization allows you to monitor the dynamic prices of your Solarbank 3 system also as member account in your hub configuration. However, since you have no control permission in that case, you cannot really automate something for your Solarbank system based on the actual or forecast prices. If you modify the provider in the mobile app, this change cannot be recognized by an integration member account. In that case, you can customize the provider manually in your HA integration and continue receiving the same prices that are also evaluated by your Solarbank system. If you modify the provider in the integration as an owner account, the change will also be applied to your system. Additionally, your system price type will automatically be changed to dynamic tariff, since that is the only way to apply a dynamic price provider setting to your system.

> [!NOTE]
> A different provider can also mean changing only the region of the same provider. The supported provider options depend on the device model type and there are countries where 'Nordpool' is offering various regions.

> [!IMPORTANT]
> In December 2025, Anker implemented a new method to support additional regional dynamic price providers. This method requires a registration through the Anker App. The price formats and Api queries for registered provides are unknown and **WILL NOT BE SUPPORTED** by the integration. Therefore, any price calculations provided by the integration may be wrong for other providers than Nordpool, since the reported pricing structure varies and is not described. With support of registered price providers, the list of standard providers has been enhanced as well. Those new providers however may not show an area code and price details cannot be queried through the Api. Furthermore, the price structure is unknown and may be different than for Nordpool. Therefore the integration  **WILL NOT SUPPORT** other providers beside Nordpool.

> [!TIP]
> If there are issues with dynamic price data or related queries, you can exclude the system price category in the hub options. This will remove all price related entities and avoid dynamic price related Api queries.

### Dynamic price fee and VAT:

Those values can be configured in the App and they are used to calculate the dynamic total price from the Nordpool spot prices as following:
> `(Spot price[per MWh] / 1000 + fee) * (1 + VAT[in %] / 100)`

Those configurable values for your system have not been found yet in Api queries, but they are essential for proper total price calculation. Since they are pretty static, you can adjust them in the integration whenever you modify them in the mobile app from time to time.

> [!NOTE]
> Once someone will find those values in Api responses, or even find a way to configure them via the Api, those entities can be changed to a similar behavior as the provider entity and be used as alternate values if the real system settings could only be queried by admin accounts.


## Modification of the appliance home load settings

The solarbank home load cannot be set directly as an individual system property. It can only be applied as schedule object, that has various plans with different structures per usage mode. While the Solarbank 1 schedule was only a single plan with a simple structure, the various usage modes of the Solarbank 2 models drastically increased variance and complexity of the schedule object. Following sections describe the options to modify the home load of your solarbank.

### Modification of Solarbank 2+ home load settings

Version 2.1.0 of the integration fully supports switching between 'Self Consumption' (`smartmeter`) or 'Custom' (`manual`) home load usage modes once a smart meter is configured in the system. Otherwise only `Custom` usage mode is typically supported. Version 2.2.0 also supports the 'Smart Plugs' (`smartplugs`) usage mode once smart plugs are configured in your Anker power system. Furthermore, the output preset can be adjusted directly, which will result in changes to the schedule rate plan applied to the solarbank. A preset change is only applied to the current time interval in the corresponding rate plan and if none exists, the rate plan or a current time interval will be created. Furthermore, all schedule actions now support modifications of any schedule rate plans, plan intervals and weekdays if supported by the rate plan.

Version 2.2.0 added support for the 'Smart Plugs' (`smartplugs`) usage mode. When this mode is active, another blend plan will be used to customize additional base load that should be added to the measured smart plug total power. The number entity that changes the output preset will therefore modify the actual time slot in the blend plan when the smart plug usage mode is active. Otherwise it will modify the actual time slot of the custom rate plan. The added system entity for `other load power` will reflect the actual extra power added based on the blend plan settings when smart plug usage mode is active. The system output preset sensor will reflect only the current setting from the custom rate plan, however this will not be applicable during Smart Plugs usage mode.

The Solarbank 2 AC or the Solarbank 3 models have pretty much the same setting capabilities as the other SB2 device models, but they provide new AC charge unique features due to their hybrid micro inverters. Version 2.5.0 of the integration provided initial support for the additional features that are unique to the AC models, like manual ['Backup charge' (`backup`)](#manual-backup-charge-option) and ['Time of Use' (`use_time`)](#time-of-use-mode) modes. For more details on these unique modes refer to [Modification of Solarbank AC settings](#modification-of-solarbank-ac-settings).

Version 3.0.0 added support for the new Solarbank 3 model, which introduced even more usage modes. A new ['Smart' (`smart`)](#smart-mode) usage mode that uses Anker Intelligence (AI) to determine best charging and discharging behavior based on previous self consumption and solar forecast data. This can be combined with dynamic utility rate plans to optimize your overall energy consumption costs. It can optionally be configured to turn on smart plugs in your system upon solar surplus for more efficient use of extra energy available in summer time.
For proper usability without PV or micro inverter attachment, beside the known 'Time of Use' mode a new ['Time Slot' (`time_slot`)](#time-slot-mode) usage mode was also added. This can automatically determine cheapest and most expensive hourly slots based on dynamic price forecast data and adjust the charging and discharging times during the day based on some metrics that you can configure.

> [!NOTE]
> The new Time Slot mode configuration is not provided in the known cloud Api structures for device schedules. Therefore this mode can only be toggled, but not configured via the integration. The same is valid for the new Smart mode. You can toggle to these new modes, but they must be initially configured or modified through the mobile app.

> [!IMPORTANT]
> General Usage mode considerations:
>   - The schedule in the Api cache is refreshed automatically with each device details refresh interval (10 minutes by default hub option settings). It may reset any temporary Api cache changes that have been made with the backup mode controls before they have been applied via an Api call.
>   - The Usage Mode selector extracts the supposed active state from the schedule object, based on actual HA server time. That means it represents the supposed active mode when system time falls into an enabled backup interval. If there are time offsets between your HA server and the Solarbank, the supposed state in the Usage Mode selector entity may be wrong.
>   - The Solarbank also reports the active usage mode as system sensor which has been added with version 2.5.0. However, due to the large delay of up to 5 minutes until the solarbank reports data updates to the cloud, you can observe significant delays of applied usage mode changes.


### Care must be taken when modifying Solarbank 1 home load settings

> [!WARNING]
> **Setting the Solarbank 1 output power for the house is not as straight forward as you might think and applying changed settings may give you a different result as expected or as represented by the output preset sensor.**

Following is some more background on this to explain the complexity. The home load power cannot be set directly for the Solarbank. It can only be set indirectly by a time schedule, which typically covers a full day from 00:00 to 24:00h. There cannot be different schedules on various days for Solarbank 1, it's only a single schedule that is shared by all solarbanks configured into the system. Typically for single solarbank systems, the solarbank covers the full home load that is defined for the time interval. For dual solarbank setups, both share 50% of the home load power preset per default. This share was fixed and could not be changed so far. Starting with the Anker App 2.2.1 and new solarbank firmware 1.5.6, the share between both solarbanks can also be modified. Starting with integration version 1.3.0, this capability is also supported with additional entities that will be created for dual solarbank systems supporting individual device presets. It is a new preset mode that was implemented in the schedule structure. Integration version 2.4.0 added support for a new discharge priority switch, which is supported for solarbank 1 with firmware 2.0.9 or higher. This allows to prioritize discharge over PV production for the power export to the house. When the Solarbank 1 will discharge, no PV production or direct bypass is possible anymore, but the requested load power according to the schedule will be discharged from the battery.

Following are the customizable parameters of a time interval that are supported by the integration and the Python Api library:
  - Start and End time of a schedule interval
  - Appliance home load preset (0/100 - 800/1600 W). If changed in dual solarbank systems, it will always use normal preset mode with the default 50% device share. Solarbank 2+ devices support lower settings down to 0 W, while Solarbank 1 devices support min. 100 W
  - For Solarbank 2+ only (ignored for Solarbank 1 systems):
      - Schedule plan to be used for the time interval
      - Week days to be  used for the time interval
  - For Solarbank 1 only (ignored for Solarbank 2+ systems):
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
  - The first generation of Solarbank E1600 is Anker's first all in one battery device for 'balcony solar systems' and was not designed for frequent home load changes. Unlike the later Solarbank 2+ systems, Solarbank 1 is only manageable via a 'fixed' time schedule and therefore was never designed to react quickly on frequent home load changes (and neither is the Api designed for it)
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

### Home load automation considerations for Solarbank 2+

The Anker mobile app actually does not support scheduled switches of the home load usage mode.
For Solarbank 2 systems with a smart meter, you can automate the switch of the home load usage mode between 'Self Consumption', 'Custom' and 'Smart plugs' if you may have the need to change this in your setup. If you have the AC model, you can also switch to 'Backup charge' and 'Time of Use' mode if applicable in your system setup.
The Solarbank 3 model can also be toggled to 'Smart' or 'Time Slot' mode if they have been initially configured via the mobile app.
Furthermore you can automate the manual appliance output preset, however this will only be applied while the 'Custom' usage mode is active. Therefore this entity is unavailable in modes not supporting it. The same is possible with the additional base power that should be added to smart plug power while 'Smart plugs' usage mode is active.

> [!WARNING]
> The integration has built-in a **cool down of 30 seconds for subsequent increases of the output preset** in order to limit the number of Api requests and schedule changes pushed by HA automation. Reductions of the output preset are not limited to always permit load reductions and prevent grid export as quickly as possible.

> [!IMPORTANT]
> It may take up to 5-6 minutes until you can seen the effect of usage plan or control changes via the integration. This is not a slow reaction of the device or the integration, but the 5 minute interval used by Solarbank 2/3 to report its latest data to the cloud. It was noticed on a Solarbank 3 system, that an applied output preset change via the integration in Manual mode was reflected almost immediately in the usage mode info of the mobile app home screen of a member account. However, the other power values may be updated with significant delay, although applied immediately with the preset change. If you need real time monitoring for the power in or our of your solarbank device, a fast smart plug that you can also integrate into Home Assistant is recommended.

---
**At this point be warned again:**

**The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library.**

---

### How can you modify the home load and the solarbank schedule

Following 3 methods are implemented to modify the home load, the schedule and/or the usage mode of your Solarbank.

> [!IMPORTANT]
> All methods require that the HA integration is configured with the owner account of your system, otherwise the defined schedule for system devices cannot be accessed or modified.

#### 1. Direct parameter changes via entity modifications

Depending on the Solarbank model, various control entities are extracted from the schedule plan and can be modified directly, like System or Device Load Preset, Charge Priority, Discharge Priority, Allow Export, etc. Any change in these control entities is immediately applied to either the current time slot in the active schedule plan, or to the general schedule structure. Please see the Solarbank dashboard screenshots above for examples of the entity representation. While the schedule is shared for the 'system appliance', each Solarbank 1 in a dual solarbank system will be presented with those entities. A change in the device load preset will however enable advanced preset mode and only change the corresponding solarbank 1 output. However, it will also result in a change of the overall system home load preset accordingly.

Starting with Solarbank 2, schedules have different plans which may be using the same or different formats. Their plan format typically has less time interval settings as for Solarbank 1 appliances and they can only define the appliance output power. However, different Solarbank 2 time schedules can be defined for various weekdays in each plan. One common setting for all plans is the solarbank usage mode. If a smart meter or smart plugs are configured in your power system, you can set the usage mode to 'Smart Meter' or 'Smart plugs' and the Solarbank will automatically adjust the appliance output to your house or smart plug demand as measured by the devices. So while you can still define a custom output schedule via the Anker mobile app, it may be applied ONLY if the solarbank lost connection to the device that is used to provide automated power demand such as the smart meter. For any gap in the defined custom plan, the default output of 200 W will be applied.
For Smart Plug usage mode the blend plan schedules will be used to add base power to smart plug measured power.
The AC model also supports a Backup charge interval definition as well as a Time of Use plan to reflect various energy tariffs and prices across daily and yearly ranges.
The Solarbank 3 additionally supports the 'Smart' mode for most efficient utilization of PV and AC power storage including automation of smart plugs upon PV surplus generation. The 'Time slot' mode can optimize AC charge and discharge behavior once a dynamic utility rate plan is used. This can lower your energy costs even without PV power generation.

**A word of caution:**

When you represent the home load number entities as input field in your dashboard cards, do **NOT use the incremental step up/down buttons in such cards** but enter the home load value directly into the number field. Each step/click via incremental field buttons triggers a setting change via Api call immediately, and increases are restricted for at least 30 seconds intervals. Preferably use a slider card for manual number modifications, since the value is just applied to the entity once you release the slider movement in the UI (do not release the slider until you moved it to the desired value).
Datetime entities in the UI are even worse, they trigger value updates for each field that is changed (date, hour, minute). To prevent Api calls upon each field change, any backup interval modification is only sent via the Api once you enable the backup switch.

Unfortunately, the HA core cards do not offer any configuration features to use number entities with input fields on your dashboard. The more info dialog typically uses the entity input mode as defined by the integration. The latest version of a very flexible HACS card called ['Custom Features for Home Assistant Cards'](https://github.com/Nerwyn/custom-card-features) allows you to enable further features for your core tile cards. Then you can easily add a number input field for the entity on your dashboard, even if the number entity is defined as slider mode.


#### 2. Solarbank schedule modifications via actions

Schedule actions are useful to apply manual or automated changes for periods that are beyond the current time interval. Following actions are available:

  - **Set new Solarbank schedule:**

    Allows wiping out the existing time intervals in the selected or active plan and defines a new time interval with the customizable schedule parameters above.

  - **Update Solarbank schedule:**

    Allows inserting/updating/overwriting a time interval in the active or selected schedule plan with the customizable schedule parameters above. Adjacent intervals will be adjusted automatically.

  - **Request Solarbank schedule:**

    Queries the actual schedule and returns the whole schedule JSON object, which is also provided in the schedule attribute of the Solarbank device output preset sensor.

  - **Clear Solarbank schedule:**

    Clear all defined solarbank schedule time intervals. The solarbank will have no longer a schedule definition and use the default output preset all day (200 W). For solarbank 2, you can optionally clear the defined intervals only for the specified weekdays of the active or specified plan.

You can specify the solarbank device ID or the entity ID of the solarbank output preset sensor as target for those actions. The Action UI in HA developer tools will filter the devices and entities that support the solarbank schedule actions. I recommend using the entity ID as target when using the action in automation, since the device ID is an internal registry value which is difficult to map to a context. In general, most of the solarbank schedule changes should be done by the update action since the Api library has built in simplifications for time interval changes. The update action follows the insert methodology for the specified interval using following rules:
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

> [!NOTE]
> Usage of Solarbank 1 advanced preset mode is determined by existing schedule structure. When no schedule is defined and the set schedule action is used with a device preset requiring the advanced power preset mode, but both solarbank 1 are not on required firmware level to accept the new schedule structure, the action call may fail with an Api request error.

#### 3. Interactive solarbank schedule modification via a parameterized script

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
  - Situations have been observed during testing with solarbank 1, where an active home load export was applied in the schedule, but the solarbank 1 did not react on the applied schedule. While the cloud schedule was showing the export enabled with a certain load set, verification in the Anker App presented a different picture: There the schedule load was set to **0 W in the slider** which is typically not possible in the App...The only way to get out of such weird schedules on the appliance is to make the interval change via the Anker App since it may use other interfaces than just the cloud Api (Bluetooth and another Cloud MQTT server). This problem was only noticed when just a single resulting interval remains in the schedule that is sent via the Api, for example setting a new schedule or making an update with a full day interval. **To avoid this problem, make sure your schedule has more than one time interval and you do NOT use the Set new Solarbank schedule action.** Instead you can apply schedule changes via the Update Solarbank schedule action with a slot that is NOT covering the full day.


## Modification of Solarbank AC settings

The Solarbank 2 AC model includes a hybrid inverter that supports also AC charging. Therefore this model supports some unique capabilities that require an additional set of sensors, control entities and actions. Note that the control entities are only present and the actions will only work for your owner account, that has permission to query and modify system and device settings.
Version 2.5.0 of the integration provided initial support for toggling the usage mode to Time of Use mode or enabling the backup charge option for the next 3 hours. Further control entities have been provided to individually set the backup charge start and end times, or to enable and disable the backup charge setting.
Version 2.6.0 added additional Time of Use plan control entities for the actual tariff and tariff price, as well as actions to modify multiple settings of these unique AC modes easily.

### Manual backup charge Option

The 'Backup charge' is considered as a usage mode option in the Anker app, since it is a temporary mode. It has a start and end timestamp and can either be active or inactive. Once active and within the defined backup charge interval, this mode will overlay any configured usage mode since it is considered as emergency charge mode for the battery. This means the battery will be charged with maximum possible charge power taken from PV or grid. Once the battery is full or the backup charge interval is exceeded, the mode will toggle back automatically to the previous configured usage mode. While the Anker App may allow only rough 30 minute interval ranges, the integration allows to specify timestamps with minute granularity (seconds are ignored), which should also be applied by the device once set in the schedule object.

#### Backup charge option control by entities

The backup charge option can be modified via control entities, which also represent the actual settings from the overall schedule object.

![AC backup charge control entities][ac-backup-control-img]

In order to avoid that each backup control entity change triggers an Api call, following behavior was implemented for the backup mode entities:
  - The UI datetime entities trigger value updates with each field change (date, hour, minute), which may result in 3 or more value update triggers for a single entity
  - Typically multiple entities need to be modified before the final backup interval definition is completed
  - To get a clear trigger for the Api call with the finalized entity changes, the backup switch entity will always be disabled once any of the backup control entities was changed in HA, either via UI entity cards or via HA entity actions.
  - Only the re-activation of the backup switch will actually trigger the Api call to update the whole backup interval with all entity changes you made. This switch activation should be made last to save the new interval via the cloud Api in the device.
    - **Note:** While any previous changes are not confirmed via the backup switch activation, they are done only in the Api cache, which can be refreshed during next device details refresh cycle. This may revert the changes you did for the backup interval entities, if they have not been applied to the cloud.
  - The App does not allow to define any backup timestamp in the past, and the end timestamp must be later than the start timestamp. These logical corrections will also be applied upon backup interval changes by the integration.
  - For convenience, the backup interval will automatically be set for the next 3 hours from now if invalid timestamps are provided
    - This default duration is sufficient to fully charge an AC device with an expansion battery
    - The backup mode will automatically be disabled when 100 % SOC is reached
  - You can also immediately enable the backup mode, just by enabling the backup switch entity or by selecting the Backup Charge mode.
    - When selecting the Backup Charge mode, the backup will always start immediately
    - If there is still a valid end timestamp in the future, this will be used instead of using the default end timestamp in 3 hours from now
  - When enabling the backup switch, the integration will apply the current backup interval via Api.
    - If the end timestamp is invalid, a default duration of 3 hours from the start timestamp is applied to the end timestamp
  - If a longer or shorter immediate backup interval is required, you just need to modify the end timestamp and reactivate the backup switch.

#### Modify AC backup charge action

You can also use an Anker Solix action to modify the backup charge settings. Following is an example of the UI mode for this action.

![AC backup charge action][ac-backup-service-img]

All fields of the action are optional. Following rules will be applied when the action is executed:
- End timestamp must be later than start timestamp
  - If timestamps are invalid while the backup switch is enabled, the start timestamp will be set to now with a default backup duration of 3 hours for the end timestamp
- If a valid end timestamp is provided, the duration field will be ignored
- If a duration is provided but the end timestamp is invalid, the duration will be added to the selected start timestamp
- Seconds are ignored when applying the timestamps via the Api
- The backup interval will only be active if the Enable toggle will be set


### Time of Use mode

A use time plan must be defined first before this mode can be enabled in the Anker app. The use time plan defines per season (range of months), at which hours during the day you have which power tariff. The app supports up to 5 season definitions, which is however not restricted in the integration. More than 5 seasons may or may not be supported by the cloud and AC device. For each season you can define peak, medium peak and off peak tariffs, as well as a valley tariff that seems to be considered as only tariff that allows AC charging from grid. For each tariff you have to define the price as well. The daily intervals are typically the same for each day, unless you specify that weekends should be different than normal weekdays. This use time plan is considered in the 'Time of Use' mode for doing a so called 'Peak and Valley' shaving. This basically means AC charge during super low tariffs and discharge only at high or peak tariffs.
I have no experience with that mode, and I found only following Anker articles that describe how the Time of Use mode works:
- Anker article: [Wie funktioniert der Nutzungszeitmodus?](https://support.ankersolix.com/de/s/article/Wie-funktioniert-der-Nutzungszeitmodus) (DE)
- Anker article: [How does the Time of Use​​​​ Mode Work?](https://support.anker.com/s/article/How-does-the-Time-of-Use-Mode-Work) (EN)

According to these tables, AC charge from grid is only done during valley tariff. During off peak tariff, discharge will only be allowed over 80% SOC, since 80% remain reserved for consumption during mid peak or peak tariffs. There is only PV charge allowed in tariffs other than valley tariff. You cannot control the charge power itself, that is controlled automatically by the Solarbank depending on SOC, temperature and available duration of the valley tariff. I assume the primary goal is to get the battery fully charged in the available valley tariff duration.
The Time of Use mode can be used only in combination with a Smart Meter or Smart Plugs, which can provide the home demand measurements for allowing automatic discharge regulation during the peak intervals, or surplus charge from internal or external PV.

#### Time of Use plan control by entities

Starting with version 2.6.0 there is a 'Tariff' select entity and a 'Tariff Price' number entity which are extracted from the defined use time plan.
Along with the system entities to control the price type, the fixed tariff price and the price currency, they complete the tariff management capabilities that the AC models offer.

![AC Time of Use service][ac-tariff-control-img]

The tariff and tariff price entities are device entities that reflect the settings from the actual interval of the use time plan, depending on season, day type and hour of the day. In order to ensure the current use time plan setting is reflected correctly in the control entities, your AC system and HA instance must be time synchronized and in the same time zone. The Time of Use plan control entities allow toggling of the actual tariff or changing the actual tariff price directly. Following rules have to be considered when using the control entities:
- Toggling to a tariff that had no previous price defined yet in the actual day type will apply your actual system fixed price as default for the selected tariff and may have to be changed afterwards
  - The default price will be adjusted to be inline with existing tariff prices
- Toggling the tariff or changing tariff prices will not cause any sanitation of the use time plan, which is typically applied when modifying the use time plan via the corresponding Anker Solix action
  - This avoids that daily time intervals are merged if same tariff exists already in adjacent intervals
  - This avoids that tariff prices are cleared if the tariff is no longer used in the daily intervals
- The price currency is also part of the use time plan definition and the Anker App allows to define different currencies per season.
  - It does not make sense to support different currencies in the same system
  - It is assumed the defined currency is only used for proper display of saving amounts, there is no amount conversion applied between different currencies or currency changes
- The currency can also be modified for the whole system and is used for the fixed price definition
- The integration will automatically use the active fixed price currency for the use time plan as well
  - That means a change of the system price currency entity will be applied automatically to an existing use time plan as well
  - The active currency is also reflected with the active tariff price number entity

#### Modify Time of Use plan action

You can also use an Anker Solix action to modify the use time plan. Following is an example of the UI mode for this action.

![AC Time of Use service][ac-time-of-use-service-img]

All fields of the action are optional. Following rules will be applied when the action is executed with inactive deletion:
- The use time plan must define all year and all day intervals, no gaps are allowed
  - Therefore any new season or day type interval will use min start and max end definition for the interval, independent which interval range was specified
  - Further intervals in the same scope must be applied with subsequent actions
- If only a start or end value is specified, this will be used to select the corresponding interval that covers the specified value
  - There will not be any change of interval ranges if no complete range was specified for the action
- Specifying a range with valid start and end will modify the specified interval in the plan
  - Adjacent intervals will be adopted accordingly to avoid overlays or gaps
  - If adjacent intervals use the same tariff type they will be merged into a single interval
  - If no tariff is provided for a new interval range, the off peak tariff will be used as default
  - If no price is provided, the active system fixed price will be used as default for selected tariff and will be adjusted to be inline with existing tariff prices
- Specifying only a price will change the active tariff price for the selected season and day type
- Specifying a tariff will modify the tariff for the selected season and day type
  - An optional price will be set or changed as well for the provided tariff
  - If no price is provided for a previously unused tariff type, the active system fixed price will be used as default
- If no day type is specified, the active day type in the selected season will be modified
  - If weekends are the same for the season, all changes will be copied to weekends as well
- If a day type is specified, only the selected day type is modified
  - This may cause weekdays to become different to weekends
- If weekdays were different from weekends but the modification makes them identical, they will be merged again for that season and marked as same

Deletions of any use time plan definitions can be performed as well with the same action once you activate the 'delete' option. Deletion is done on various scopes of the plan and depends on which other options have been specified. A general deletion rule is to remove also the higher level scope object and fill any gaps if the last interval in the lower level scope is deleted.

Following rules will be applied once the 'delete' option is used:
- If start or end hour is specified, the time interval(s) from given or selected day type and season will be removed
  - If only one of the time range options is specified, only the selected single interval will be removed
  - If a range is specified, the given range will be removed and the gap will be closed by adjacent intervals
- Otherwise if a tariff is specified, the tariff will be removed from selected or active day type and season
  - All time intervals with the specified tariff will be removed and the gaps will be closed by adjacent intervals
  - The tariff price definition will be removed as well
- Otherwise if a day type is specified, removal will be done as following:
  - If a dedicated day type is specified and current types are different, the other day type will be used as remaining definition and day types will be made same
  - If all day types are specified or current types are the same, the season will be removed and the gap will be closed by adjacent seasons
- Otherwise if start or end month is specified, the season(s) will be removed and the gap will be closed by adjacent seasons
  - If only one of the month range options is specified, only the selected single season will be removed
  - If a range is specified, the given month range will be removed and the gap will be closed by adjacent seasons
- Otherwise the whole use time plan will be removed if no further options are specified

Removal of intervals can lead to a gap in the overall range. Likewise the removal of the last interval (or last tariff) could result in an empty day type or season. Both must be prevented to maintain a valid use time plan. Following common rules will be applied to avoid gaps or holes in required use time plan ranges:
- The remaining previous time interval will be elongated to fill the gap of the removed time range
  - The following interval will be used from the beginning if no previous time interval remains
- If no time interval remains for the day type, the day types of the season will be made same if they were different
  - Otherwise the whole season will be deleted and the season gap will be closed by adjacent seasons
- A remaining previous season will be elongated to fill the gap of the removed season range
  - The following season will be used from the beginning if no previous season remains
- If no season remains, the whole use time plan will be removed

#### Usage of flexible tariffs with the Time of Use mode

The use time plan must be manually defined with time intervals and prices for the whole year. No gaps are allowed in the plan. Therefore the Time of Use mode may be useful for a flexible tariff structure if available by your energy provider, but definitely not for dynamic hourly tariff prices as offered by energy providers in many countries.
An added Time of Use plan action of the Anker Solix integration supports dynamic modifications of the use time plan, which can be used in HA automation and scripts to adjust the use time plan tariffs and prices dynamically once the hourly structure of the next day is known. If you plan to implement such an automation for your Solarbank 2 AC and you have the required dynamic tariff entities or forecast information available in your HA instance, I recommend to define only a single season and single day type with all tariff intervals and prices that you need for the next day. Run the automation one time a day and overwrite any previous definitions, to ensure the action will not insert or split more seasons or time intervals than absolutely necessary. This will keep your use time plan as simple as possible. To overwrite all existing time intervals with the first new interval, you need to specify the full day range with the start and end hour options (00:00 - 23:59). Further new intervals can then be inserted with their specified time range, tariff type and price.


## Modification of Solarbank 3 settings

### Smart mode

The Smart mode is designed to optimize your overall energy consumption and lower energy cost by Anker Intelligence (AI). You need to make your own opinion, how intelligent this mode really operates, but it includes PV production forecast data as well as price forecast of an optional [dynamic utility rate plan](#dynamic-utility-rate-plans-options) or a defined flexible [use time plan](#modify-time-of-use-plan-action). You need to authorize Anker for data collection, you need Google Maps on the Anker mobile App device and you need to locate your home for accurate PV forecast data. For optional dynamic prices, you also have to configure the dynamic utility rate plan options (price provider, price fee and tax) if not done yet. For the optional flexible tariff you have to define a use time plan or you can enter a [fixed price for your system](#toggling-system-price-type-or-currency-settings) if you have a fix price tariff. Furthermore you can configure smart plugs with the Smart mode and prioritize the order of the automated plugs if PV surplus will occur. They can help to avoid unnecessary power export to the grid by temporary use of power consumers in your house.

#### Usage of Smart mode

> [!IMPORTANT]
> The Smart mode configuration will not be provided by the integration and requires the mobile app anyway to admit all required authorizations. Therefore this mode can only be toggled once configured, but not setup or modified via the integration.

Various options that may be used in the Smart mode however can be configured by the integration, such as a [use time plan](#modify-time-of-use-plan-action) with flexible tariffs, or the [fix price settings](#toggling-system-price-type-or-currency-settings) and the [price provider for dynamic utility rate plans](#price-provider-for-dynamic-utility-rate-plans). The integration also provides additional sensors and attributes to monitor parameters of the Smart mode:
  - AI enablement and training status
  - AI monitoring runtime and status
  - AI price advantage through Smart mode usage
  - Smart plug sensor to show whether plug is automatically switched by Smart mode and in which priority

### Time Slot mode

The Time slot mode was specifically introduced for utility rate plans with dynamic tariffs. Beside configuration of a dynamic price provider, you only have to configure buying price fees and taxes as well as optional selling tariff and fees. Furthermore you need to configure time slot options for charging and discharging durations. The mode will then automatically determine the best charging and discharging periods based on tariff forecast data of the configured spot price provider. This mode may be useful, if you do not have any solar panels attached and want to use the Solarbank only as AC storage device to utilize Peak and Valley shaving of your dynamic tariff.

#### Usage of dynamic tariffs with the Time Slot mode

> [!IMPORTANT]
> The Time slot mode configuration is currently not provided in the known cloud Api structures for device schedules. Therefore this mode can only be toggled, but not setup or modified via the integration.

To allow monitoring of dynamic price forecast as used by your solarbank, customizable number entities are provided by the integration to [configure purchase fee and tax](#dynamic-price-fees-and-taxes). They are used by the integration to calculate the total dynamic tariff price for your system. The total price is also reflected in the forecast data, which are provided as attribute of the total dynamic price sensor. There is also a dynamic spot price sensor, which has more details about the polled provider, timestamp, and spot price averages in its attributes.


## Toggling system price type or currency settings

Prior to the release of the Solarbank 2 AC model, only a single fixed price could be defined for your Solarbank system, which is used by the Anker Cloud to calculate your overall savings. Once you have defined a use time plan with different tariffs for your system, the system price type can be toggled to the defined use time plan tariffs. This is supposed to make more accurate total saving calculations by the cloud, but it is difficult to validate. It turned out, that enabling the Time of Use mode in the Anker App will automatically toggle the system price type to Time of Use price. However, toggling away from Time of Use mode does not automatically revert system price type back to the previous type. And it also might not make sense to do so. The same is valid once a dynamic price provider is toggled or the Time Slot mode is activated. This can only be applied while activating the dynamic price type for your system at the same time. However, the price type is not toggled back once toggling away from Time Slot mode.

> [!NOTE]
> If you toggle your system price currency entity via the integration, the currency change will also be applied to all currency definitions in an existing use time plan. The Anker App will not do that automatically.

### Dynamic utility rate plans options

The Solarbank 3 electricity provider configuration allows definition of various new settings for your system price configuration. Some are supported already by the integration version 3.0.0, others may be supported in future if the required Api queries have been identified by the community.

#### Dynamic price provider

There may be one or more dynamic price provider options available for your Solarbank 3 system, depending on the country your Anker account is using. Typically this is 'Nordpool' for most countries, but others may be supported in future. A provider is defined via country, company and area code. Therefore multiple provider options may be presented already by the integration, if there are multiple regions supported by your country company. Any supported combination of those provider options can be chosen via a select entity. If you modify the provider as an owner account, the provider selection will be applied to your system and the dynamic price type will automatically be enabled, which is required to apply a provider selection. If you modify the provider as a member account, the change is only applied to the Api cache, but not activated on the system since your account has no permission for such a modification. The selected provider however will be used by the integration to poll spot price forecast data via the Anker cloud. The spot price data can be polled independently of your system type or access permission.

> [!IMPORTANT]
> Be aware of the limitations and support for [dynamic price provider selection](#dynamic-price-provider-selection).

#### Dynamic price fees and taxes

The dynamic price fee and value added tax (VAT) of your system configuration actually cannot be determined or modified through the cloud Api. While those entities are provided as customizable number entities in the integration, the changes are only applied as customization to the Api cache, but **NOT** to your real system configuration. However, their data is required to calculate the total dynamic prices (actual and forecast) as used by your system to evaluate charge and discharge slots as well as saving calculations. Monitoring the spot prices for your device model is also possible as system member. However, to calculate total dynamic prices and forecast data also for system members, those entities have been made customizable for the Api cache for now. They will be initialized with an average default for your country if defined.

#### Export tariff options

The dynamic price options in the mobile App allow definition of selling price options with export tariff type and fee.

> [!IMPORTANT]
> None of these options was found in the Api structures and they are currently not implemented at all in the integration.


## Solar forecast data

The Solarbank 3 mode was the first Anker Solix device that supports solar forecast data. Other devices like the X1 may follow.
One important fact about forecast data for the Solarbank 3 is that they are provided through the cloud only when your device is running in 'Smart' mode.
Then you can see the forecast also in your mobile app solar chart for today and tomorrow. The forecast data is limited to next 24h, so they do NOT cover the full next day typically. Therefore the presented 24h forecast energy may not be that usable, depending on your home usage pattern over the day.
The integration version 3.1.0 added support to query the solar forecast data and presents them in following two system entities:
  - sensor.system_*name*_solar_forecast_today
  - sensor.system_*name*_solar_forecast_this_hour

The cloud only provides hourly energy values for the next 24 hours. No history of past hours for today is provided. The integration enhances this data with additional information, such as forecast for this and next hour, total forecast for today, remaining forecast for today as well as the poll time and the hourly values for today and available hours for tomorrow. The integration utilizes the entity restore capability to maintain the forecast history of today whenever the integration is reloaded or HA is being restarted. Therefore you typically do not loose them if the Api cache has to be rebuilt from scratch upon new connections.
The remaining energy for today is calculated only from the forecast data. The total forecast for today is calculated from available forecast data. If data polling started in the middle of the day and no history is available, the past hour production data is used to calculate a more accurate total forecast.
Along the solar forecast data collection, the integration also calculates the hourly solar production for today from the provided cloud data and adds them as new attribute to the existing `sensor.system_*name*_daily_solar_yield` entity. This allows you to compare the hourly forecast data with the daily production data as demonstrated in the [forecast data example diagram](#apex-chart-card-to-show-forecast-data).

![forecast-data-diagram][forecast-data-diagram-img]

If you want to track older hourly history data, you can use the state tracking of your `sensor.system_*name*_solar_forecast_this_hour` entity and compare it with the hourly averaged state values of your `sensor.system_*name*_sb_solar_power` entity. The hourly power average corresponds to the forecast energy of the hour if the power state intervals are pretty similar.
Forecast data entities and cloud polling can be excluded in your hub configuration options with the Solarbank Energy category.

> [!IMPORTANT]
> None of the forecast entities can be used as solar forecast entities for your HA energy dashboard. If Smart mode is inactive, no forecast data is provided and the entities will show an unknown state. Furthermore those entities are not designed to integrate with your HA energy dashboard. Instead they are usable to monitor the behavior of the 'Smart' mode since that is acting like a black box and may show weird charging and discharging behavior that may not make much sense. If you need more accurate forecast data, I recommend any of the available solar forecast integrations.


## Modification of vehicles

Each Anker cloud user can create up to 5 Electric Vehicles (EV). Vehicles will be used to manage charge orders for an Anker Solix V1 EV Charger device, which can be shared amongst Anker cloud users. The integration currently does **NOT** yet support the vehicle creation itself, but it creates a virtual device for each existing EV under the user account. Various vehicle attributes can be modified, the possible selections depend on the EV database that is used by the Anker cloud. If you want to remove the vehicle from your user account, you can simply remove the vehicle device in your integration hub configuration as shown on following vehicle device screenshot.

![vehicle-device][vehicle-device-img]

Following capabilities are implemented as of version 3.2.0:
- Any existing vehicle definition will be added as vehicle device that is connected to your account device
- All vehicle attributes can be modified, after the default attributes have been set based on brand/model/year/model-ID selection
- A model ID selection will reset the attributes to the defined attributes of that model ID
- All selection options will be queried from the Anker cloud vehicle database and cached in the Api cache for better performance of electable options
- Vehicles can be removed from your account by removing the device in HA
- Vehicle related devices and entities can be completely deactivated by excluding the Vehicles category in your hub configuration options

> [!TIP]
> The integration will automatically discover added and removed vehicles under the user account during the regular device details refresh cycle (10 minutes per default). An immediate vehicle refresh can also be triggered manually by a corresponding button of the account device.

![account-vehicle-refresh][account-vehicle-refresh-img]

A future release of the integration may also provide a configuration flow to create new user vehicles via the integration.


## Markdown card to show the defined Solarbank schedule

### Markdown card for Solarbank 1 schedules

Following markdown card code can be used to display the solarbank 1 schedule in the UI frontend. The active interval will be highlighted. Just replace the entity with your sensor entity representing solarbank effective output preset. It is the sensor that has the schedule attribute.

![markdown-card][schedule-markdown-img]

#### Markdown card code for Solarbank 1 schedules

<details>
<summary><b>Expand to see card code</b><br><br></summary>

```yaml
type: markdown
content: |
  {% set entity = 'sensor.solarbank_e1600_home_preset' %}
  {% set datatime = 'sensor.system_solarbank_sb_data_time' %}
  {% set isnow = (now()+timedelta(seconds=state_attr(datatime,'tz_offset_sec')|int(0))).replace(second=0,microsecond=0) %}
  {% set slots = (state_attr(entity,'schedule')).ranges|default([])|list %}
  ### Solarbank 1 Schedule - Local time: {{isnow.strftime("%H:%M")}}
  {% if slots %}
    {{ "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s"|format('Start', 'End', 'Preset', 'Export', '▼Prio', '▲Prio', 'Mode', 'SB1', 'SB2', 'Name') }}
    {{ ":---:|:---:|---:|:---:|:---:|:---:|:---:|---:|---:|:---" }}
  {% else %}
    {{ "No schedule available"}}
  {%- endif -%}
  {%- for slot in slots -%}
    {%- set bs = '_**' if strptime(slot.start_time,"%H:%M").time() <= isnow.time() < strptime(slot.end_time.replace('24:00','23:59'),"%H:%M").time() else '' -%}
    {%- set be = '**_' if bs else '' -%}
    {%- set sb2 = '-/-' if slot.device_power_loads|default([])|length < 2 else slot.device_power_loads[1].power~" W" -%}
      {{ "%s | %s | %s | %s | %s | %s | %s | %s | %s | %s"|format(bs~slot.start_time~be, bs~slot.end_time~be, bs~slot.appliance_loads[0].power~" W"~be, bs~'On'~be if slot.turn_on else bs~'Off'~be, bs~'On'~be if slot.priority_discharge_switch|default(false) else bs~'Off'~be, bs~slot.charge_priority~' %'~be, bs~(slot.power_setting_mode or '-')~be, bs~slot.device_power_loads[0].power~" W"~be, bs~sb2~be, bs~slot.appliance_loads[0].name)~be }}
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

### Markdown card for Solarbank 2+ schedules

Following markdown card code can be used to display the Solarbank 2+ schedule in the UI frontend (including optional smart mode stats, custom_rate_plan, blend_plan, use_time plan and manual_backup plan if defined). The active interval in the active plan will be highlighted. Just replace the entities at the top with your sensor entities representing the corresponding device and system entities. If you do not have corresponding AI entities, you can leave them as is since the Smart mode section is only shown once usable in your system.

> [!IMPORTANT]
> The markdown card is very sensitive for proper formatting of printed characters. Markdown tables may not be correctly formatted if indents are wrong, for example caused by indents of the template code.

![markdown-3-card][schedule-3-markdown-img]

#### Markdown card code for Solarbank 2+ schedules

<details>
<summary><b>Expand to see card code</b><br><br></summary>

```yaml
type: markdown
content: >
  {% set entity = 'sensor.solarbank_3_home_preset' %}
  {% set usage = 'select.solarbank_3_usage_mode' %}
  {% set ai_state = 'binary_sensor.solarbank_3_ai_enabled' %}
  {% set ai_mon = 'sensor.system_solarbank_ai_monitoring' %}
  {% set datatime = 'sensor.system_solarbank_sb_data_time' %}
  {% set mode = states(usage) %}
  {% set isnow = (now()+timedelta(seconds=state_attr(datatime,'tz_offset_sec')|int(0))).replace(second=0,microsecond=0) %}
  {% set schedule = state_attr(entity,'schedule')|default({}) %}
  {% set plan = ((state_attr(entity,'schedule')).custom_rate_plan|default([]))|list %}
  ### SB Schedule (Usage Mode: {{state_translated(usage)}}) - Local: {{isnow.strftime("%H:%M")}}
  {% if 'smart' in state_attr(usage,'options')|default([]) %}
    {%- set bs = '_**' if mode == 'smart' else '' -%}
    {%- set be = '**_' if bs else '' %}
    ### Anker Intelligence
    {{bs~'Enabled: '~state_translated(ai_state)~(' *' if bs else '')~' ('~state_attr(ai_state,'status')|capitalize~')'~be}}
    {{'Monitor: '~state_translated(ai_mon)~' - Runtime: '~state_attr(ai_mon,'runtime')}}
  {% endif %}
  {% for plan_name,plan in (schedule or {}).items() %}
    {% if plan_name in ['custom_rate_plan','blend_plan'] and plan -%}
      {%- set week = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"] -%}
      {%- set active = (mode=='smartplugs' and plan_name=='blend_plan') or (mode=='manual' and plan_name=='custom_rate_plan')-%}
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
      {%- for idx in (plan.ranges or [])|default([]) %}
        {%- set start = idx.start_time|as_datetime|as_local -%}
        {%- set end = idx.end_time|as_datetime|as_local -%}
        {%- set bs = '_**' if switch and start.time() <= isnow.time() < end.time() else '' -%}
        {%- set be = '**_' if bs else '' %}
    {{ "%s | %s | %s"|format(bs~start.strftime("%d.%m.%y %H:%M")~be, bs~end.strftime("%d.%m.%y %H:%M")~be,'*' if be else '') }}
      {%- endfor %}
    {% endif %}
    {% if plan and plan_name in ['use_time'] %}
      {%- set tariffs = ["Peak","Medium","OffPeak","Valley"] -%}
      {%- set active = mode=='use_time' %}
      {% for sea in plan|default({}) -%}
        {%- set unit = sea.unit|default('-') -%}
        {%- set wk = sea.weekday|default([]) -%}
        {%- set we = sea.weekend|default([]) -%}
        {%- set m_start = isnow.replace(day=1,month=(sea.sea|default({})).start_month|default(1)|int(1)) -%}
        {%- set m_end = isnow.replace(day=1,month=(sea.sea|default({})).end_month|default(12)|int(12)) -%}
        {%- set is_same = sea.is_same|default(true) %}
    {{ '**Season: '~[m_start.strftime("%b"),m_end.strftime("%b")]|join(' - ')~',   Weekends: '~('SAME' if is_same else 'DIFF')~'  ('~plan_name~')**' }}
    {{ "%s | %s | %s | %s | | %s | %s | %s | %s"|format('Start', 'End', 'Type', 'Price', 'Start', 'End', 'Type', 'Price') }}
    {{ ":---|:---|:---|---|---|:---|:---|:---|:---" }}
        {#- Show different weekend side by side in season -#}
        {% for idx in range(max(wk|length,we|length)) -%}
          {%- if wk|length > idx -%}
            {%- set tariff = wk[idx].type|default(0)|int(0) -%}
            {%- set price = sea.weekday_price | selectattr('type',"eq",tariff) | map(attribute='price') | list | first | float(0) -%}
            {%- set tariff = tariffs[tariff-1] if tariff is number and 0 < tariff <= tariffs|length else '------' -%}
            {%- set start = today_at(wk[idx].start_time|default(0)|string~":0") -%}
            {%- set end = wk[idx].end_time|default(0)|int(0) -%}
            {%- set end = today_at(end|string~":0") if end < 24 else today_at("0:0") + timedelta(days=1)  -%}
            {%- set bs = '_**' if active and m_start.month <= isnow.month <= m_end.month and isnow.weekday() in range(5) and start.time() <= isnow.time() < end.time() else '' -%}
            {%- set be = '**_' if bs else '' -%}
            {%- set row = "%s | %s | %s | %s%.2f %s | |"|format(bs~start.strftime("%H:%M")~be, bs~end.strftime("%H:%M")~be, bs~tariff~be, bs, price, unit~be~('*' if bs else '')) -%}
          {%- else -%}
            {%- set row = " | | | | | | " -%}
          {%- endif %}
          {%- if not is_same and we|length > idx -%}
            {%- set tariff = we[idx].type|default(0)|int(0) -%}
            {%- set price = sea.weekend_price | selectattr('type',"eq",tariff) | map(attribute='price') | list | first | float(0) -%}
            {%- set tariff = tariffs[tariff-1] if tariff is number and 0 < tariff <= tariffs|length else '------' -%}
            {%- set start = today_at(we[idx].start_time|default(0)|string~":0") -%}
            {%- set end = we[idx].end_time|default(0)|int(0) -%}
            {%- set end = today_at(end|string~":0") if end < 24 else today_at("0:0") + timedelta(days=1)  -%}
            {%- set bs = '_**' if active and m_start.month <= isnow.month <= m_end.month and isnow.weekday() in range(5,7) and start.time() <= isnow.time() < end.time() else '' -%}
            {%- set be = '**_' if bs else '' -%}
            {%- set row = row ~ "%s | %s | %s | %s%.2f %s"|format(bs~start.strftime("%H:%M")~be, bs~end.strftime("%H:%M")~be, bs~tariff~be, bs, price, unit~be~('*' if bs else '')) -%}
          {%- else -%}
            {%- set row = row ~ " | | | " %}
          {%- endif %}
    {{ row }}
        {%- endfor %}
      {% endfor %}
    {% endif %}
  {% endfor %} {% if not plan %}
    {{ "No schedule available"}}
  {% endif %}
```
</details>

**Notes:**

- Shared accounts have no access to the schedule
- Solarbank 2+ devices have less settings per custom plan time slot than Solarbank 1, making it easier to adjust
- Solarbank 2+ custom plan schedules can be created for individual weekdays. Each group of weekdays has its own plan ID. A weekday can only be configured into one plan ID
- The defined `custom_rate_plan` is only used when the usage mode is set to 'Custom' (`manual`) or 'Self Consumption' (`smartmeter`) for the case of smart meter communication loss
- The defined `blend_plan` is only used when the usage mode is set to 'Smart plugs' (`smartplugs`)
- The `manual_backup` plan is only used for the 'Backup charge' mode of models supporting AC charge. It will overlay any other mode if enabled and in defined datetime interval.
- The `use_time` plan is only used when the 'Time of Use' mode is enabled
- The `time_slot` plan is only used for 'Time Slot' mode. However, currently there is not supplied any object for the time_slot plan through the cloud Api, therefore the structure and configuration parameters are unknown. Once they become available, the markdown card will be revised with this additional plan of Solarbank 3 devices
- The Anker Intelligence (AI) section is just shown if the device supports the `Smart` mode
- Highlighting of the active plan and slot is based on local timezone of the device. The local timestamp is provided in the card header


## Apex chart card to show forecast data

The [Apex chart card](https://github.com/RomRider/apexcharts-card) can be installed from the [HA Community Store](https://www.hacs.xyz/). It is a very customizable and flexible card to display diagrams of your entities. Following is an example card to demonstrate how you can extract the fields from the hourly attributes of forecast and solar yield entities. Just replace the entity_id's with your sensor entity_id representing the corresponding entity.

![forecast-data-diagram][forecast-data-diagram-img]


#### Apex chart card code for forecast data

<details>
<summary><b>Expand to see card code</b><br><br></summary>

```yaml
type: custom:apexcharts-card
header:
  title: Price & Solar Forecast
  show: true
  show_states: true
  colorize_states: true
graph_span: 48h
span:
  start: day
  offset: +0h
now:
  show: true
  label: Now
yaxis:
  - id: price
    decimals: 2
    min: auto
    max: 0.6
    show: true
    apex_config:
      tickAmount: 12
      axisBorder:
        show: true
  - id: energy
    decimals: 0
    opposite: true
    min: auto
    max: 600
    show: true
    apex_config:
      tickAmount: 12
      axisBorder:
        show: true
apex_config:
  chart:
    height: 350px
    width: 105%
    offsetX: -10
    zoom:
      enabled: true
  plotOptions:
    bar:
      columnWidth: 80%
      borderRadius: 2
  group_by:
    duration: 1h
all_series_config:
  type: area
  stroke_width: 3
  opacity: 0.2
  extend_to: now
  show:
    legend_value: false
    offset_in_name: false
    in_header: false
experimental:
  color_threshold: true
series:
  - entity: sensor.system_solarbank_dyn_price_total
    name: Price €/kWh
    unit: €/kWh
    yaxis_id: price
    offset: "-0.5h"
    float_precision: 4
    data_generator: |
      let res = [];
      for (const item of Object.values(entity.attributes.forecast)) {
        res.push([new Date(item.timestamp).getTime(), item.price]);
      }
      return res;
    color_threshold:
      - value: 0
        color: LimeGreen
      - value: 0.2
        color: GreenYellow
      - value: 0.25
        color: gold
      - value: 0.3
        color: tomato
      - value: 0.35
        color: red
    type: column
    opacity: 0.5
    stroke_width: 0
    show:
      extremas: true
  - entity: sensor.system_solarbank_solar_forecast_today
    name: Solar forecast Wh
    yaxis_id: energy
    unit: Wh
    float_precision: 0
    offset: "-0h"
    data_generator: |
      let res = [];
      for (const item of Object.values(entity.attributes.forecast_hourly)) {
        res.push([new Date(item.timestamp).getTime(), item.power]);
      }
      return res;
    color: LemonChiffon
    stroke_dash: 3
  - entity: sensor.system_solarbank_daily_solar_yield
    name: Solar yield Wh
    yaxis_id: energy
    unit: Wh
    float_precision: 0
    offset: "-0h"
    data_generator: >
      let res = []; for (const item of Object.values(entity.attributes.produced_hourly)) {
        if (item.power != '') {
          res.push([new Date(item.timestamp).getTime(), item.power]);
        }
      } return res;
    color: yellow
    opacity: 0.6
```
</details>


## Script to manually modify appliance schedule for your solarbank

With Home Assistant 2024.3 you have the option to manually enter parameters for a script prior execution. This is a nice capability that let's you add an UI capability for an action right into your dashboard. You just need to create a script with input fields that will run the selected solarbank action using the entered parameters. Following is a screenshot of the more info dialog for the script entity:

![Change schedule script][schedule-script-img]

In order to run the script interactively from the dashboard, you just need to add an actionable card and select the script as entity with the action to show the more-info dialog of the script. If you place the schedule markdown card on the left or right column of the dashboard, you can review the active schedule while entering the parameters for the changes you want to apply. That gives you similar schedule management capabilities as in the Anker App...Nice.

**Notes:**

- You may have to reload your browser window when the changed or inserted schedule intervals are not directly represented in the markdown card
- See further notes above for adjusting the appliance home load parameters or schedule when things are behaving differently than expected

Below are example scripts which you can use for either Solarbank 1 or Solarbank 2+ devices, you just need to replace the entity name in the action data entity_id field with your device sensor that represents the output preset and has the schedule attribute. If you have multiple systems, you can make the entity also a selectable field in the script similar to the action. For dual solarbank systems, you just need one of the 2 solarbank preset entities to apply the change, since the schedule is shared.

### Script code to adjust Solarbank 1 schedules

<details>
<summary><b>Expand to see script code</b><br><br></summary>

```yaml
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
</details>

### Script code to adjust Solarbank 2+ schedules

<details>
<summary><b>Expand to see script code</b><br><br></summary>

```yaml
alias: Change Solarbank 2+ Schedule
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

### Script code to adjust Solarbank AC backup charge

<details>
<summary><b>Expand to see script code</b><br><br></summary>

```yaml
alias: Modify AC backup charge
description: ""
icon: mdi:battery-clock
mode: single
fields:
  entity:
    name: Entity
    description: Choose a SB AC entity
    required: true
    default: switch.solarbank_2_ac_backup_option
    selector:
      entity:
        integration: anker_solix
        domain: switch
  backup_start:
    name: Backup start
    description: >-
      Start date and time of the backup period in the form YYYY-MM-DD HH:MM:SS. Default is active period start or now.
    required: false
    example: "2025-02-24 13:00:00"
    selector:
      datetime: null
  backup_end:
    name: Backup end
    description: >-
      End date and time of the backup period in the form YYYY-MM-DD HH:MM:SS. Default is active period end or now + 3 hours.
    required: false
    example: "2025-02-24 17:00:00"
    selector:
      datetime: null
  backup_duration:
    name: Backup duration
    description: >-
      Duration of the backup period in the form HH:MM:SS. Used only if no backup end is specified instead of default duration of 3 hours.
    required: false
    example: "04:00:00"
    selector:
      duration: null
  enable_backup:
    name: Enable backup period
    description: Enable or disable the defined or active backup period
    required: false
    example: true
    selector:
      boolean: null
sequence:
  - action: anker_solix.modify_solix_backup_charge
    target:
      entity_id: |
        {{entity}}
    data:
      backup_start: |
        {{backup_start|default(None)}}
      backup_end: |
        {{backup_end|default(None)}}
      backup_duration: |
        {{backup_duration|default(None)}}
      enable_backup: |
        {{enable_backup|default(None)}}
```
</details>

### Script code to adjust Solarbank AC Time of Use plan

<details>
<summary><b>Expand to see script code</b><br><br></summary>

```yaml
alias: Modify AC Time of Use
description: ""
icon: mdi:cash-clock
mode: single
fields:
  entity:
    name: Entity
    description: Choose a SB AC entity
    required: true
    default: select.solarbank_2_ac_tariff
    selector:
      entity:
        integration: anker_solix
        domain: select
  start_month:
    name: Start month
    description: Start month for the season to be modified
    required: false
    default: jan
    selector:
      select:
        mode: dropdown
        multiple: false
        translation_key: month
        options:
          - jan
          - feb
          - mar
          - apr
          - may
          - jun
          - jul
          - aug
          - sep
          - oct
          - nov
          - dec
  end_month:
    name: End month
    description: End month for the season to be modified
    required: false
    default: dec
    selector:
      select:
        mode: dropdown
        multiple: false
        translation_key: month
        options:
          - jan
          - feb
          - mar
          - apr
          - may
          - jun
          - jul
          - aug
          - sep
          - oct
          - nov
          - dec
  day_type:
    name: Day type
    description: Type of the days to be modified in the season
    required: false
    example: all
    selector:
      select:
        mode: dropdown
        multiple: false
        translation_key: daytype
        options:
          - weekday
          - weekend
          - all
  start_hour:
    name: Start hour
    description: Start hour of the days to be modified (minutes and seconds are ignored)
    required: false
    default: "00:00:00"
    selector:
      time: null
  end_hour:
    name: End hour
    description: >-
      End hour of the days to be modified (minutes and seconds are ignored). For 24:00 you must enter 23:59
    required: false
    default: "23:59:00"
    selector:
      time: null
  tariff:
    name: Tariff
    description: Tariff to be used for the selected or active period
    required: false
    default: off_peak
    selector:
      select:
        mode: dropdown
        multiple: false
        translation_key: tariff
        options:
          - peak
          - mid_peak
          - off_peak
          - valley
  tariff_price:
    name: Tariff price per kWh
    description: Tariff price per kWh for the selected or active period
    required: false
    example: 0.27
    default: 0.3
    selector:
      number:
        min: 0
        max: 1
        step: 0.01
        unit_of_measurement: per kWh
  delete:
    name: Delete selected options from plan
    description: >-
      If activated, the selected options will be removed from the plan instead of being created or modified. Deletions will always merge ranges in the
      applicable scope to avoid any gaps. If no option is selected, the whole plan will be deleted.
    required: false
    selector:
      boolean: null
sequence:
  - action: anker_solix.modify_solix_use_time
    target:
      entity_id: |
        {{entity}}
    data:
      start_month: |
        {{start_month|default(None)}}
      end_month: |
        {{end_month|default(None)}}
      day_type: |
        {{day_type|default(None)}}
      start_hour: |
        {{start_hour|default(None)}}
      end_hour: |
        {{end_hour|default(None)}}
      tariff: |
        {{tariff|default(None)}}
      tariff_price: |
        {{tariff_price|default(None)}}
      delete: |
        {{delete|default(None)}}
```
</details>


## Other integration actions

Anker Solix actions can be used in any automation, script or via the HA UI developer tool panel.

> [!NOTE]
> The Anker Solix actions are registered only in HA after the first hub configuration was loaded. All actions also require specific target entities with selected features to be used with the action. If no eligible entities are provided with the action target selector, the action cannot be utilized either.

### Export systems action

Starting with version 2.1.2, a new action was added to simplify an anonymized export of known Api information available for the configured account. Version 3.4.0 added the option to include MQTT messages in the export, which is enabled per default. The Api responses will be saved in JSON files and the folder will be zipped in your Home Assistant configuration folder (where your `configuration.yaml` is located, e.g. `/homeassistant`), under `www/community/anker_solix/exports`. The `www` folder in your configuration folder is the local file folder for the HA dashboard to access files directly via the browser. It is also used by custom dashboard cards. Home Assistant automatically maps the `www` folder to `/local` in the URL path if the folder exists at HA startup. The action response field `export_filename` will provide the zipped filename url path as response to the action. This allows easy download from your HA instance through your browser when navigating to that url path. Optionally you can download the zip file via Add Ons that provide file system access.

![Export systems service][export-systems-service-img]

> [!IMPORTANT]
> If the system export just created the `www` folder on your HA instance, it is not mapped yet to the `/local` folder and cannot be accessed through the browser. You have to restart your HA instance to have the new `www` folder mapped to `/local`.

**Notes:**

- This action will execute a couple of Api queries and run about 10 or more seconds. **If Api throttling must be used, it may even run 1-3 minutes.**
- If **MQTT messages are included**, the runtime will be **at least 5 minutes** to allow gathering of standard message types as well as including a 60 second interval of real time messages
- **The UI button will only show green once the action is finished.** An error will be raised if the action is retriggered while there is still a previous action active, or while the configuration startup is not completed yet.
- There may be logged warnings and errors for queries that are not allowed or possible for the existing account. The resulting log notifications for the anker_solix integration can be cleared afterwards
- The url path that is returned in the response needs to be added to your HA server hostname url for direct download of the zipped file (the `www` filesystem folder is accessible as `/local` in the url navigation path as given in the response).

### Get system info action

Starting with version 2.0.0, a new action was added for the system total yield entity in order to query the overall system information from the cloud Api, which contains the data that is presented on the Anker App home page screen. This data is used by the integration to represent most but not all of the entities. It may be helpful to debug what values are actually available on the Api cloud at the time requesting them. Following is an example screenshot showing only the top of the response:

![Get system info service][get-system-info-service-img]

Version 2.3.0 added an option to include cached data in the presented response, so additional fields as cached or merged by the Api library may be shown.

### Get device info action

Starting with version 3.4.1, a new action was added for the device refresh details button entity in order to obtain all cached information about the device. This data is used by the integration to represent all device entities, whether they are provided through the Api or the MQTT connection. Optionally you can include the MQTT cache data, which will also include the raw data fields as extracted from the received MQTT messages, based on the mapping descriptions for the device model number. It may be helpful to debug device values, and compare which device Api and MQTT data may be merged. Following is an example screenshot showing only the top of the response:

![Get device info service][get-device-info-service-img]

### Api request action

Starting with version 2.6.0, a new action was added to simplify exploration of Anker Solix Api requests for your systems and devices. It allows you to place 'GET' or 'POST' requests to any endpoints you select or enter manually. It is recommended to use the action from the HA developer tools panel, either in the UI or YAML version. The request responses or errors will be shown in the action result window. Many endpoints require usage of an owner account due to permissions for device information. Weird and non-descriptive Anker Api error messages and codes may be returned if system owner permission is missing. Other queries may not list complete information if your Anker hub entry used for the Api request does not have owner permissions to the systems.

Following is an example of such an Api request action in YAML mode (including parameter templating):
![Api request service][api-request-img]

Example of a bad request with missing parameters in UI mode:
![Bad Api request][api-bad-request-img]

Example of a valid request but missing system permissions (shared account only):
![Missing Permission Api request][api-missing-permission-request-img]

#### Hints and tips when using Api requests

* There is no documentation which endpoints exist or which parameters and options or methods to be used for various endpoints
* The known endpoints are documented in the [integration repo module apitypes.py](https://github.com/thomluther/ha-anker-solix/blob/main/custom_components/anker_solix/solixapi/apitypes.py#L98)
  - Example parameters for used endpoints can be found in the source code as well, especially the [export.py module](https://github.com/thomluther/ha-anker-solix/blob/main/custom_components/anker_solix/solixapi/export.py)
* There are various endpoint categories listed:
  - Account related endpoints:
    - `passport/*`
  - App related endpoints:
    - `app/*`
  - Generic Api or balcony power endpoints:
    - `power_service/v1/*`
  - Charging systems endpoints like Power Panels:
    - `charging_energy_service/*`
    - **Note:** Those endpoints are currently not supported on the EU cloud server
  - Home energy systems (HES) endpoints like X1:
    - `charging_hes_svc/*`
  - Power Charger categories:
    - `mini_power/v1/app/*`
  - Unknown categories:
    - `charging_disaster_prepared/*`
* Most endpoints use the POST method, only some need the GET method. The error typically refers to an unknown method if the wrong method was used
* Some errors may show the missing mandatory parameters of the payload. If parameters are used in the wrong format, the error may also describe that.
  - However, most of the time the parameter usage can be discovered only by trial and error until you got it right
  - Unfortunately it will be difficult to discover optional parameters and how they may change the response information
* Standalone device information in the Anker cloud is pretty rare
  - Typically you cannot find (all) device details as they are being presented in the Anker mobile App, for example device temperature
  - Some are only available via the Anker MQTT cloud server or via Bluetooth interface
* If you find new requests or useful information in responses that are not available yet via the integration, open an [issue as feature request][issues] and document them there
  - Implementation into the integration can then be considered
  - You will have to provide detailed documentation of required parameters and various responses at different times, especially when it comes to proper interpretation of any status codes or conditions that may exist only temporarily or barely.
  - Any abstract field values in responses will have to be mapped to meaningful descriptions by you before they can be implemented in the integration. I think no user will have any benefit from a `connection_status` of `1` or `2` when they are presented as sensor...
* You can integrate this action also in scripts or automation to implement queries or change settings that are not implemented in the Anker Solix integration (yet)
  - However, this action does not integrate directly into the Api cache which is used by the data update coordinator to refresh all entity states
  - Any changes that will be applied by this action will not be reflected until the next data refresh or device details refresh cycle is completed
  - Further delays may occur if the devices post their data updates only in 5 minute intervals to the cloud

#### Format of the payload

The request payload must be a JSON object, which typically consists of named parameter value fields and/or lists. Values can be basic types like boolean, int, float or string values. But they can also be objects or lists and therefore be nested. Following is a basic guideline how you have to format your YAML input for the payload parameter to have it properly converted to JSON structures.
- Basic type values are specified as number (int), decimal (float), true/false (boolean) or text with or without quotes (string)
  - Use quotes to enforce any value interpretation as string
- A new object is started by a new line with indent
  - All parameters with same indent belong to the object
- A new list is also started by a new line with indent
  - Each list item starts with a dash, indicating start of new list item
  - Each parameter with the same indent belongs to the same list item
- You can also use Jinja templating for the values like for other HA automation or scripts
- To specify a Jinja template, you can specify:
  - A quoted template string in the same line as the parameter
  - End the parameter line with `>` or `|` character and start the template in new lines with indent

Example:
```yaml
  payload:
    parm_bool: true
    parm_int: 1
    parm_float: 1.0
    parm_text: "text1"
    parm_list_items:
      - text1
      - text2
      - text3
    parm_list_objects:
      - item_1_int: 2
        item_1_float: 2.0
        item_1_text: "text2"
        item_1_bool: false
        item_1_template: "{{ 'string_a' == 'string_b' }}"
      - item_2_int: 3
        item_2_float: 3.0
        item_2_text: "text3"
        item_2_bool: true
        item_2_template: |
          {{device_attr('sensor.sb_e1600_solar_power','serial_number')}}
```

Templating is a big advantage when using the action in HA, since the requests often require the site_id or device_sn parameters, which can easily be pulled from the device attributes of any of your system or device entity IDs. Following is an example to query the site price settings (replace the entity IDs with any of yours):

```yaml
action: anker_solix.api_request
target:
  entity_id: switch.lol_de_api_usage
data:
  method: post
  endpoint: power_service/v1/site/get_site_price
  payload:
    device_sn: |
      {{device_attr('sensor.sb_e1600_solar_power','serial_number')}}
    site_id: |
      {{device_attr('sensor.system_bkw_daily_solar_yield','serial_number')}}
```


## Showing Your Appreciation

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)][buy-me-coffee]

If you like this project, please give it a star on [GitHub][anker-solix]
***

[anker-solix]: https://github.com/thomluther/ha-anker-solix
[releases]: https://github.com/thomluther/ha-anker-solix/releases
[releases-shield]: https://img.shields.io/github/release/thomluther/ha-anker-solix.svg?style=for-the-badge
[issues]: https://github.com/thomluther/ha-anker-solix/issues
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
[options-img]: doc/options-v2.png
[options-api-img]: doc/options-api.png
[options-mqtt-img]: doc/options-mqtt.png
[repair-issue-img]: doc/repair-issue.png
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
[schedule-3-markdown-img]: doc/schedule-3-markdown.png
[schedule-script-img]: doc/change-schedule-script.png
[schedule-service-img]: doc/schedule-service.png
[request-schedule-img]: doc/request-schedule.png
[solarbank-2-system-dashboard-img]: doc/solarbank-2-system-dashboard.png
[solarbank-2-pro-device-img]: doc/Solarbank-2-pro-device.png
[solarbank-2-pro-diag-img]: doc/Solarbank-2-pro-diag.png
[smart-meter-device-img]: doc/Smart-Meter-device.png
[get-system-info-service-img]: doc/get-system-info-service.png
[get-device-info-service-img]: doc/get-device-info-service.png
[export-systems-service-img]: doc/export-systems-service.png
[api-refresh-sensors-img]: doc/api-refresh-sensors.png
[api-refresh-history-img]: doc/api-refresh-history.png
[api-request-img]: doc/api-request.png
[api-bad-request-img]: doc/api-bad-request.png
[api-missing-permission-request-img]: doc/api-missing-permission-request.png
[ac-backup-control-img]: doc/ac-backup-control.png
[ac-backup-service-img]: doc/ac-backup-service.png
[ac-tariff-control-img]: doc/ac-tariff-control.png
[ac-time-of-use-service-img]: doc/ac-time-of-use-service.png
[dynamic-price-diagram-img]: doc/dynamic-price-diagram.png
[forecast-data-diagram-img]: doc/forecast-data-diagram.png
[power-dock-device-img]: doc/power-dock-device.png
[vehicle-device-img]: doc/vehicle-device.png
[account-vehicle-refresh-img]: doc/account-vehicle-refresh.png
[account-mqtt-entities-img]: doc/account-mqtt-entities.png
[device-mqtt-diag-entities-img]: doc/device-mqtt-diag-entities.png
[entity-attributes-img]: doc/entity-attributes.png
[mqtt-statistics-img]: doc/mqtt-statistics.png



