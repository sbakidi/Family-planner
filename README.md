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

Install the requirements as above and set the `TEST_MODE_ENABLED` environment
variable so an in-memory test database is used. Then run the tests:

```bash
export TEST_MODE_ENABLED=1
pytest
```

You can also run `make test`, which sets up the database and invokes `pytest`
automatically.
