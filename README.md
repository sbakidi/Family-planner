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

### API Usage

Authenticate and obtain a token:

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"email": "user@example.com", "password": "password"}'
```

Use the returned token with other endpoints:

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:5000/api/v1/events
```

## Running Tests

Install the requirements as above and run:

```bash
pytest
```

This will execute the unit tests for the API and manager modules.
