"""Amazon Alexa skill integration using Flask-Ask."""

from flask import Flask

try:
    from flask_ask import Ask, statement, question
except ImportError:  # pragma: no cover - dependency may not be installed in tests
    Ask = None
    statement = lambda text: text
    question = lambda text: text

from src import event_manager

class AlexaAssistant:
    """Simple wrapper for handling Alexa intents."""

    def __init__(self, app: Flask, route: str = "/alexa"):
        if Ask is None:
            raise ImportError("flask_ask package required for Alexa integration")
        self.app = app
        self.ask = Ask(app, route)
        self._register_intents()

    def _register_intents(self) -> None:
        @self.ask.intent('AddEventIntent', mapping={'title': 'Title', 'start': 'Start', 'end': 'End'})
        def add_event(title, start, end):
            event_manager.create_event(title=title, description='', start_time_str=start, end_time_str=end)
            return statement(f"Added event {title}")

        @self.ask.intent('QueryScheduleIntent', mapping={'user_id': 'User'})
        def query_schedule(user_id):
            events = event_manager.get_events_for_user(int(user_id))
            titles = ', '.join(e.title for e in events) if events else 'no events'
            return statement(f"Schedule has {titles}")
