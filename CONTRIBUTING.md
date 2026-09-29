# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Exploring and documenting MQTT messages of Solix devices

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!
    - If the change modifies the solixapi library files, create the pull request in the [anker-solix-api library](https://github.com/thomluther/anker-solix-api) for those files, since the HA integration just uses a copy of the anker-solix-api library.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](https://github.com/thomluther/ha-anker-solix/issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](https://github.com/thomluther/ha-anker-solix/issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)
- For issues and new feature requests, you should also provide an [anonymized system export zip file](https://github.com/thomluther/ha-anker-solix/blob/main/INFO.md#export-systems-action)

People *love* thorough bug reports. I'm not even kidding.

## Contribute with Api exploration and MQTT message decoding and description

If you have no Python knowledge, you can contribute by exploring the Anker Solix Api via the [Api request action](INFO.md#api-request-action) and document your discovery of new, unknown Api request capabilities and information about your owned Anker Solix devices that you still miss in the integration.
If you don't find any data for your owned devices although you enabled the MQTT server connection, your device model still has to be decoded and described. You can contribute by starting with the [mqtt_monitor tool](https://github.com/thomluther/anker-solix-api#mqtt_monitorpy) from the [Api library](https://github.com/thomluther/anker-solix-api) and follow the [MQTT data decoding guidelines](https://github.com/thomluther/anker-solix-api/discussions/222). In order to decode MQTT commands of your device, please follow this [MQTT command and state analysis and description](https://github.com/thomluther/anker-solix-api/discussions/222#discussioncomment-14660599).


## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

This custom component is based on [integration_blueprint template](https://github.com/ludeeus/integration_blueprint).

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
