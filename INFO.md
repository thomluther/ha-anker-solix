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

Following are anonymized examples how the Anker power devices will be presented (Screenshots are from initial release without changable entities):

**1. System Device**

![System Device][system-img]
![Connected Devices][connected-img]

**2. Solarbank Device**

![Solarbank Device][solarbank-img]

**3. Inverter Device**

![Inverter Device][inverter-img]

Following are screenshots from basic dashboard cards including the latest sensors and all changable entites that are available when using the system main account:

**4. Dark Theme examples**

![System Dashboard][system-dashboard-img] ![Solarbank Dashboard][solarbank-dashboard-img]

**5. Light Theme examples**

![Solarbank Dashboard Light Theme][solarbank-dashboard-light-img]


**Note:** When using a shared system account for the integration, device detail information is limited and changes are not premitted. Therefore shared system account users may get presented no changable entities by the integration.

The integration will setup the entities with unique IDs based on device serials or a combination of serial numbers. This makes them truly unique and provides the advantage that the same entities can be re-used after switching the integration configuration to another shared account. While the entity history is not lost, it implies that you cannot configure different accounts at the same time when they share a system. Otherwise, it would cause HA setup errors because of non unique entities. Therefore, new integration configurations are validated and not allowed when they share systems or devices with an active configuration.
If you want to switch from your main account to the shared account, delete first the active configuration and then create a new configuration with the other account. When the devices and entities for the configured account will be created, deleted entities will be re-activated if their data is accessible via Api for the configured account. That means if you switch from your main account to the shared account, only a subset of entities will be re-activated. The other deleted entities and their history data may remain available until your configured recorder interval is over. The default HA recorder history interval is 10 days.


## Data refresh configuration options

The data on the cloud which can be retrieved via the Api is refreshed only once per minute. Therefore, it is recommended to leave the integration refresh interval set to the default minimum of 60 seconds, or increase it even further when no frequent updates are required. Refresh intervals are configurable from 30-600 seconds, but **less than 60 seconds will not provide more actual data and just cause unnecessary Api traffic.** Version 1.1.0 of the integration introduced a new system sensor showing the timestamp of the delivered Solarbank data to the cloud, which can help you to understand the age of the data.

**Note:** The solarbank data timestamp is the only device category timestamp that seems to provide valid data (inverter data timestamp is not updated by the cloud).

During each refresh interval, the power sensor values will be refreshed, along with the actual system configuration and available end devices. There are more end device details available showing their actual settings, like power cut off, auto-upgrade, schedule etc. However, those details require much more Api queries and therefore are refreshed less frequently. The device details refresh interval can be configured as a multiplier of the normal data refresh interval. With the default options of the configured account, the device details refresh will run every 10 minutes, which is typically by far sufficient. If a device details update is required on demand, each end device has a button that can be used for such a one-time refresh. However, the button will re-trigger the device details refresh only when the last refresh was more than 30 seconds ago to avoid unnecessary Api traffic.

The cloud Api also enforces a request limit but actual metrics for this limit are unknown. You may see the configuration entry flagged with an error, that may indicate 429: Too many requests. In that case, all entities may be unknown or show stale data until further Api requests are permitted. To avoid hitting the request limit, a configurable request delay was introduced with version 1.1.1. This may be adjusted to avoid too many requests per second. Furthermore the Solarbank energy statistic entities which were introduced with verion 1.1.0 have been excluded from the configuration entry per default. They may increase the required Api requests significantly as shown in the discussion post [Api request overview](https://github.com/thomluther/hacs-anker-solix/discussions/32).
The statistics can be re-enabled by removing them from the exclusion list. Future enhancements will add more exclusion options for categories and device types that are of no interest. This may help further to reduce the required Api requests and customize the configuration to the entity types that are meaningful to you.

The refresh options can be configured after creation of an integration entry. Following are the default options as of version 1.1.1:

![Options][options-img]

**Note:** When you add categories to the exclusion list, the affected entities are removed from the HA registry during integration reload but they still show up in the UI as entities no longer provided by the integration. You need to remove those UI entities manually from the entity details dialog.


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
1. Just now you can access the system as a member. The owner will also get a confirmation that you accepted the invitation.


## Automation to send and clear sticky, actionable notifications to your smart phone based on Api switch setting

Following automation can be used to send a sticky actionable notification to your Android mobile when the companion app is installed. It allows you to launch the Anker app or to re-activate the Api again for your system.

![notification][notification-img]

Make sure to replace the entities used in the example below with your own entities. The system variable is automatically generated based on the device name of the entity that triggered the state change.

**Note:** If you want to modify the notification to work with your iPhone, please refer to the [HA companion App documentation](https://companion.home-assistant.io/docs/notifications/notifications-basic/) for IOS capabilities.

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
          - service: notify.my_smartphone
            alias: Send notification to smartphone
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

## Modification of the appliance home load settings

### Care must be taken when modifying the home load settings

**Attention: Setting the solarbank output power for the house is not as straight forward as you might think and applying changed settings may give you a different result as expected or as represented by the output preset sensor.**

Following is some more background on this to explain the complexity. The home load power cannot be set directly for the solarbank. It can only be set indirectly by a time schedule, which typically covers a full day from 00:00 to 24:00h. There cannot be different schedules on various days, it's only a single schedule that is shared by all solarbanks configured into the system. Typically for single solarbank systems, the solarbank covers the full home load that is defined for the time interval. For dual solarbank setups, both share 50% of the home load power preset per default. This share was fixed and could not be changed so far. Starting with the Anker App 2.2.1 and new solarbank firmware 1.5.6, the share between both solarbanks can also be modified. However, this capability is not built into the Python library for the time being. It's not clear how the share can be modified via the cloud Api and you need a dual solarbank setup to explore those capabilities.

Following are the customizable parameters of a time interval that are supported by the integration and the Python Api library:
- Start and End time of a schedule interval
- Appliance home load preset (0-800 W), using the default 50% share in dual solarbank setups
- Export switch
- Charge Priority Limit (0-100 %), typically only seen in the App when Anker MI80 inverter is configured

Those given ranges are being enforced by the integration and the Api library. However, while those ranges are also accepted by the appliance when provided via a schedule, the appliance may ignore them when they are outside of its internally used/defined boundaries. For example, you can set an Appliance home load of 50 W which is also represented in the schedule interval. The appliance however will still apply the internal minimum limit of 100 W or 150 W depending on the configured inverter type for your solarbank.
It is typically the combination of those 3 settings, as well as the actual situation of the battery SOC, the temperature and the defined/used inverter in combination with either the charge priority setting or activation of the 0 W switch that all determine which home load preset will be applied by the appliance. The applied home load is typically represented in the App for the active time interval, and this is what you can also see in the Solarbank System sensor for the preset output power. But rest assured, even if it shows 0 W home load preset is applied, it does not warrant you there won't be any output power to the house!

### To conclude: The appliance home load preset for the solarbank is just the desired output, but the truth can be completely different

Before you now start using the home load preset modification capability in some fancy real time automations for zero grid power export, here is my advise:

**Forget it !!!**

I will also tell you why:
- The Solarbank E1600 is Anker's first all in one battery device for 'balcony solar systems' and was not designed for frequent home load changes. Up to now it is only manageable via a 'fixed' time schedule and therefore was never designed to react quickly on frequent home load changes (and neither is the Api designed for it)
- The Solarbank reaction on changed home load setting got better and during tests a typical adoptions of 15-60 seconds for smaller home load changes with firmware 1.5.6 have been observed. However, it is still far too slow for real/near time power automations, since all data communication occurs only via the cloud and has significant value time lags to be considered.
- In reality (as an avergage) you need to allow the solarbank up to 1-2 minutes until you get back reliable sensor values from the cloud that represent the result of a previous change. The solarbank also sends the data only once per minute to the cloud, which is another delay to factor into your automation.
- If you have additional and local (real time) sensors from smart meters or inverters, they might help to see the modification results faster. But still, the solarbank is too slow until it settled reliably for a changed home load. Furthermore it all depends on the cloud and internet availability for any automation. Alternativaly I recommend to automate the solarbank discharge only locally via limiting the inverter when you have real time automation capabilities for your inverter limits. [I realized this project as described in the forum](https://community.home-assistant.io/t/using-anker-solix-solarbank-e1600-in-ha/636063) with Hoymiles inverter, OpenDTU and a Tasmota reader device for the grid meter and that works extremly well.
  - **Attention:** Don't use the inverter limit during solar production since this will negatively impact your possible solar yield and the solarbank may end up in crazy power regulations all the time.
- Additionally, each parameter or schedule change requires 2 Api requests, one to submit the whole changed schedule and another one to query the applied and resulting schedule again for sensor updates. To enforce some protection for the Api and accomodate the slow solarbank reaction, an increase of the home load is just allowed every 30 seconds at least (decreases or other interval parameter changes are not limited)
  - **Attention:** Cloud Api requests are limited, but actually the enforced limits in regards to quantity and time frames are unknown. Each change may bring you towards the enforced limit and not only block further changes, but also render all integration entities unavailable or stale
- If you have some experience with the solarbank behavior, you may also know how weird it sometimes reacts on changed conditions during the day (or even unchanged conditions). This makes it difficult to adjust the home load setting automatically to a meaningful value that will accomplish the desired home load result.
- If you plan to automate moderate changes in the home load, use a timer helper that is restarted upon each change of the settings and used as condition for validation whether another change (increase) should be applied. I would not recommend to apply changes, especially increases in the home load, in less than 2-3 minute intervals, a trusted re-evaluation of the change results and further reaction can just be done after such a delay. Remember that each Solarbank datapoint is just a single value of a one minute interval. The value average in that interval can be completely different, especially if you compare Solarbank data with real time data of other power devices in your home!

Meaningful automation ideas that might work for the solarbank:
- Use schedule serivces to apply different set of schedules for different weekdays (workday, homeoffice, weekend etc). The Anker App does not provide this capability, but with HA automations you could create new schedules for given days in advance. Use first the Set schedule service which will create a new all day interval and then Update schedule service to insert additional intervals as needed. Try the service sequence manually to validate if they accomplish the desired end result for your schedule.
- Use solar forecast data to define a proper home load preset value for the day in order to allow the battery charging is spanning over the whole day while using as much direct solar power as possible in the house. This will prevent that the battery is full before noon in summer and then maximum solar power is bypassed to the house but cannot be consumed. This is something that I plan implementing for this summer since I have already built an automation for recommended home load setting...
- Use time to time changes in the home load when you have expected higher consumption level for certain periods, e.g. cooking, vacuum cleaning, fridge cooling, etc. Basically anything that adds a steady power consumption for a longer period. Don't use it to cover short term consumers like toaster, electric kettles, mixer or coffee machines. Also the home load adoption for washing machines or laundry dryer might not be very effective and too slow since they are pretty dynamic in power consumption.
- You have probably more automation ideas for your needs and feel free to share them with the community. But please keep the listed caveats in mind to judge whether an automation project makes sense or not. All efforts may be wasted at the end if the appliance does not behave as you might expect.

**At this point be warned again:
The user bears the sole risk for a possible loss of the manufacturer's warranty or any damage that may have been caused by use of this integration or the underlying Api python library.**


### How can you modify the home load and the solarbank schedule

Following 3 methods are implemented with version 1.1.0 of the integration:

#### 1. **Direct parameter changes via entity modifications for Appliance Home Load preset, allowance of export and charge priority limit**

Any change in those 3 entities is immediately applied to the current time slot in the existing schedule. Please see the Solarbank dashboard screenshots above for examples of the entity representation.

**A word of caution:**

When you represent the home load number entity as input field in your dashboard cards, do **NOT use the step up/down arrows** but enter the home load value directly in the field. Each step via the field arrows triggers a settings change immediately, and increases are restricted for min. 30 second intervals. Preferrably use a slider for manual number modifications, since the value is just applied to the entity  once you release the slider movement (do not release the slider until you moved it to the desired value).

#### 2. **Solarbank schedule modifications via services**

They are useful to apply manual or automated changes for times that are beyond the current time interval. Following 3 services are available:
  - **Set new Solarbank schedule:** Allows wiping out the defined schedule and defines a new interval with the customizable schedule parameters above
  - **Update Solarbank schedule:** Allows inserting/updating/overwriting a time interval in the existing schedule with the customizable schedule parameters above. Adjacent intervals will be adjusted automatically
  - **Request Solarbank schedule:** Queries the actual schedule and returns the whole schedule JSON object, which is also provided in the schedule attribute of the Solarbank device output preset sensor.

You can specify the solarbank device id or the entity ID of the solarbank output preset sensor as target for those services. The service UI in HA developper tools will filter the devices and entities that support the solarbank schedule services. I recommend using the entity ID as target when using the service in automations since the device ID is an internal registry value which is difficult to map to a context. In general, most of the solarbank schedule changes should be done by the update service since the Api library has built in simplifications for time interval changes. The update service follows the insert methodology for the specified interval using following rules:
  - Adjacent slots are automatically adjusted with their start/end times
    - Completely overlayed slots are automatically removed
    - Smaller interval inserts result in 1-3 intervals for the previous time range, depending on the update interval and existing interval time boundaries
    - For example if the update interval will be within an existing larger interval, it will split the existing interval at one or both ends. So the insert of one interval may result in 2 or 3 different intervals for the previous time range.
  - Gaps will not be introduced by schedule updates
  - If only the boundary between intervals needs to be changed, update only the interval that will increase because updating the interval that shrinks will split the existing interval
    - When one of the update interval boundaries remains the same as the existing interval, the existing interval values will be re-used for the updated interval in case they were not specified.
    - This allows quick interval updates for one boundary or specific parameters only without the need to specify all parameters again
  - All 3 parameters are mandatory per interval for a schedule update via the Api. If they are not specified with the service, existing ones will be re-used when it makes sense or following defaults will be applied:
    - 100 W Home load preset
    - Allow Export is ON
    - 80 % Charge Priority limit
  - The Set schedule service also requires to specify the time interval for the first slot. However, testing has shown that the provided times are ignored and a full day interval is always created when only a single interval is provided with a schedule update via the Api.

#### 3. **Interactive solarbank schedule modification via a parameterized script that executes a schedule service with provided parameters**

Home Assistant 2024.3 provides a new capability to define fields for script parameters that can be filled via the more info dialog of the script entity prior execution. This allows easy integration of schedule modifications to your dashboard (see example script and dashboard below).


Following are screenshots showing the schedule service UI panel (identical for Set schedule and Update schedule service), and the Get schedule service with an example:

**1. Set or Update schedule service UI panel example, using the entity as target**

![Update schedule service][schedule-service-img]

**2. Get schedule service example, using the device as target**

![Get schedule service][request-schedule-img]


While not the full entity ranges supported by the integration can be applied to the device, some may provide enhanced capabillities compared to the Anker App. Following are important notes and limitations for schedule modifications via the Cloud Api:
- Time slots can be defined in minute granualrity and what I have seen, they are also applied (don't take my word for given)
- The end time of 24:00 must be provided as 23:59 since the datetime range does not know hour 24. Any seconds that are specified are ignored
- Homeassistant and the Solarbank should have simlar time, but especially same timezone to adopt the time slots correctly. Even more important it is for finding the current/active schedule time interval where individual parameter changes must be applied
  - Depending on the front end (and timezone used with the front end), the time fields may eventually be converted. All backend datetime calculations by the integration use the local time zone of the HA host. The HA host must be in the same time zone the Solarbank is using, which is typically the case when they are on the same local network.
- Situations have been observed during testing where an active home load export was applied in the schedule, but the solarbank did not react on the applied schedule. While the cloud schedule was showing the export enabled with a certain load set, verification in the Anker App presented a different picture: There the schedule load was set to **0 W in the slider** which is typically not possible in the App...The only way to get out of such weird schedules on the appliance is to make the interval change via the Anker App since it may use other interfaces than just the cloud Api (Bluetooth and another Cloud MQTT server)


## Markdown card to show the defined Solarbank schedule

Following markdown card code can be used to display the solarbank schedule in the UI frontend. Just replace the entity with your sensor entity that represents the
solarbank effective output preset. It is the sensor that has the schedule attribute.

![markdown-card][schedule-markdown-img]

```
type: markdown
content: |
  ## Solarbank Schedule

  {% set entity = 'sensor.solarbank_e1600_home_preset' %}
  {% set slots = (state_attr(entity,'schedule')).ranges|default([])|list %}
  {% set isnow = now().time().replace(second=0,microsecond=0) %}
  {% if slots %}
    {{ "%s | %s | %s | %s | %s | %s | %s | %s"|format('Start', 'End','Preset','Export','Prio', 'SB1', 'SB2', 'Name') }}
    {{ ":---:|:---:|---:|:---:|:---:|---:|---:|:---" }}
  {% else %}
    {{ "No schedule available"}}
  {% endif %}
  {% for slot in slots -%}
    {%- set bs = '_**' if strptime(slot.start_time,"%H:%M").time() <= isnow < strptime(slot.end_time.replace('24:00','23:59'),"%H:%M").time() else '' -%}
    {%- set be = '**_' if bs else '' -%}
    {%- set sb2 = '-/-' if slot.device_power_loads|default([])|length < 2 else slot.device_power_loads[1].power~" W" -%}
      {{ "%s | %s | %s | %s | %s | %s | %s | %s"|format(bs~slot.start_time~be, bs~slot.end_time~be, bs~slot.appliance_loads[0].power~" W"~be, bs~'On'~be if slot.turn_on else bs~'Off'~be, bs~slot.charge_priority~' %'~be, bs~slot.device_power_loads[0].power~" W"~be, bs~sb2~be, bs~slot.appliance_loads[0].name)~be }}
  {% endfor -%}
```

**Notes:**
- Shared accounts have no access to the schedule
- The schedule values show the individual customizable settings per interval. The reported home load preset that is 'applied' and shown in the system preset sensor state as well as in the Anker App is a combined result from the appliance for the current interval settings.
- The applied appliance home load preset can show 0 W even if appliance home load preset is different, but Allow Export switch is off. It also depends on the state of charge and the charge priority limit and the defined/installed inverter. Even if the preset sensor state shows 0 W, it does not mean that there won't be output to the house. It simply reflects the same value as presented in the App for the current interval.
- Starting with Anker App 2.2.1, you can modify the default 50 % preset share between a dual Solarbank setup. The SB1 and SB2 values of the schedule will show the applied preset per Solarbank in that case, which is also reflected in the individual device preset sensor. For single Solarbank setups, the individual device presets of the schedule are ignored by the appliance and the appliance preset is used.
- Even if each Solarbank device has its own Home Preset sensor (reflecting their contribution to the applied home load preset for the device) and schedule attribute, all Solarbanks in a system share the same schedule. Therefore a parameter change of one solarbank also affects the second solarbank. The applied home load settings are ALLWAYS for the schedule, which is still shared by all solarbanks in the system.



## Script to manually modify appliance schedule for your solarbank

With Home Assistant 2024.3 you have the option to manually enter parameters for a script prior execution. This is a nice capability that let's you add an UI capability for a service right into your dashboard. You just need to create a script with input fields that will run the selected solarbank service using the entered parameters. Following is a screenshot of the more info dialog for the script entity:

![Change schedule script][schedule-script-img]

Below is an example script which you can use, you just need to replace the entity name in the service data entity_id field with your device sensor that represents the output preset and has the schedule attribute. If you have multiple systems, you can make the entity also a selectable field in the script similar to the service. For dual solarbank systems, you just need one of the 2 solarbank preset entities to apply the change, since the schedule is shared.

```
alias: Change Solarbank Schedule
fields:
  service:
    name: Service
    description: Choose which service to use
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
    name: Home load preset
    description: Watt to be delivered to the house
    required: false
    default: 100
    selector:
      number:
        min: 0
        max: 800
        step: 10
        unit_of_measurement: W
  allow_export:
    name: Allow export
    description: >-
      If deactivated, the battery is not discharged or, if an MI80 inverter or 0 W switch is installed, the charging priority is used without exporting to the house
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
      {{service}}
    target:
      entity_id: sensor.solarbank_e1600_home_preset
    data:
      start_time: |
        {{start_time}}
      end_time: |
        {{end_time}}
      appliance_load: |
        {{appliance_load|default(None)}}
      allow_export: |
        {{allow_export|default(None)}}
      charge_priority_limit: |
        {{charge_priority_limit|default(None)}}
mode: single
icon: mdi:sun-clock
```

In order to run the script interactively from the dashboard, you just need to add an actionable card and select the script as entity with the action to show the more-info dialog of the script. If you place the schedule markdown card on the left or right column of the dashboard, you can review the active schedule while entering the parameters for the changes you want to apply. That gives you similar schedule management capabilities as in the Anker App...Nice.

**Notes:**
- You may have to reload your browser window when the changed or inserted schedule intervals are not directly represented in the markdown card
- See further notes above for adjusting the appliance home load parameters or schedule when things are bevaving differently than expected


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
[solarbank-dashboard-img]: doc/solarbank-dashboard.png
[solarbank-dashboard-light-img]: doc/solarbank-dashboard-light.png
[system-dashboard-img]: doc/system-dashboard.png
[schedule-markdown-img]: doc/schedule-markdown.png
[schedule-script-img]: doc/change-schedule-script.png
[schedule-service-img]: doc/schedule-service.png
[request-schedule-img]: doc/request-schedule.png


