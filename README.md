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

## Plugins

The application supports simple plugins located in `src/plugins/`. Each plugin
is a Python module that defines a `Plugin` class with a `name` attribute and a
`register(app)` method. Optional cleanup can be provided with an
`unregister(app)` method.

Place your plugin file in `src/plugins/` and restart the application. Visit
`/admin/plugins` in the web interface to enable or disable discovered plugins.

### Example Plugin

```python
# src/plugins/sample.py
from flask import Blueprint

bp = Blueprint("sample", __name__)

@bp.route("/sample")
def hello():
    return "Hello from sample plugin"

class Plugin:
    name = "Sample"

    def register(self, app):
        app.register_blueprint(bp)
```
