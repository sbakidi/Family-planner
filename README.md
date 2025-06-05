# Family Planner

A simple planner application with a Flask API and command line interface for managing users, children, events and shifts.

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
