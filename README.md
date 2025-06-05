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
