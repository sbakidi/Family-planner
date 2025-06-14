
# Family-planner

Family-planner
Een eenvoudige planner voor ouders om diensten, evenementen en verblijfsperiodes van kinderen te beheren.

## Installation

Install the required Python packages before running the application or its tests:

## Installatie

1. Zorg dat Python 3 geïnstalleerd is.
2. (Aanbevolen) Maak en activeer een virtual environment:
   ```bash
   # Zorg ervoor dat je python3 en pip voor python3 gebruikt
   python3 -m venv venv
   # Op Windows:
   # venv\Scripts\activate
   # Op macOS/Linux:
   # source venv/bin/activate
   ```bash
   pip install -r requirements.txt
   ```

## CLI gebruiken

Start de commandoregelinterface met:

# Family Planner

A simple planner application with a Flask API and command line interface for managing users, children, events and shifts.

### New Feature: Grocery Lists

The API now supports simple shared grocery items. Items can be created,
viewed, updated and deleted via `/grocery-items` endpoints.

## Setup

Install the required packages using pip:


```bash
pip install -r requirements.txt
```


The application uses SQLite by default. Running the app will create a local database file if it does not exist.

## Usage

### Command Line
Run the CLI to manage data from the terminal:


```bash
python main.py
```


## Flask-app gebruiken

De webapplicatie start je met:
```bash
python app.py
```
Deze draait standaard op `http://localhost:5000`.

## Tests uitvoeren

Alle unittests kun je draaien met:
```bash
python -m unittest discover
```

### Flask Web App
Start the web interface:

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## Running Tests

Install the requirements as above and run:

```bash
pytest
```

This will execute the unit tests for the API and manager modules.


## Notifications

The application exposes a server-sent events endpoint at `/notifications/stream`.
Authenticated web clients automatically subscribe and will receive JSON messages
when shifts or events are created or updated. Mobile clients can listen to this
endpoint to display real-time notifications.

## Google Calendar Sync

To enable Google Calendar integration you need API credentials from the
[Google Cloud Console](https://console.cloud.google.com/). Create an OAuth
"Web application" or "Desktop" client and download the `credentials.json` file.

Place the file in the project root (or update `CLIENT_SECRETS_FILE` in
`src/calendar_sync.py`) and ensure the OAuth consent screen includes the
callback URL `http://localhost:5000/oauth2callback` if using a web flow.

Once credentials are configured you can authorize and sync a user's calendar
from the CLI using the "Sync Google Calendar" option or by calling the API
endpoint `/users/<user_id>/calendar/sync`.

## Mobile App

The `mobile_app/` directory contains a minimal React Native project built with Expo.

### Setup

Install Node.js (v18+) and run the following commands inside `mobile_app`:

```bash
npm install
```

### Running

Start the Expo development server:

```bash
npx expo start
```

Use the Expo app or an emulator to view the login and calendar screens. The app expects the Flask API to be running locally at `http://localhost:5000`.



