# Voice Assistant Integration

This package integrates the Family Planner with Amazon Alexa and Google Assistant.

## Requirements

* `flask-ask` for Alexa support
* `google-assistant-sdk` for Google Assistant support

Install them with:

```bash
pip install flask-ask google-assistant-sdk
```

## Registering an Alexa Skill

1. Go to the [Amazon Developer Console](https://developer.amazon.com/).
2. Create a new **Custom** skill and note the Skill ID.
3. Set the endpoint to your application URL where the `AlexaAssistant` is mounted.
4. Define intents `AddEventIntent` and `QueryScheduleIntent` with the slots used in `alexa.py`.
5. Enable account linking if you want per-user schedules.

## Registering a Google Action

1. Visit the [Actions Console](https://console.actions.google.com/) and create a new project.
2. Choose **Dialogflow** or **Actions SDK** for your fulfillment.
3. Point the fulfillment webhook to the endpoint running `GoogleAssistant`.
4. Create intents for adding an event and querying a schedule.

Refer to the respective platform documentation for details on certificates and deployment.
