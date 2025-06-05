import json
from datetime import datetime
from typing import List

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.exc import SQLAlchemyError

from src.database import SessionLocal
from src.user import User
from src.event_manager import create_event

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRETS_FILE = 'credentials.json'


def _store_credentials(user: User, creds: Credentials, db):
    """Persist the OAuth credentials JSON for a user."""
    user.calendar_token = creds.to_json()
    db.commit()


def authorize_user(user_id: int) -> Credentials:
    """Run local OAuth flow and store the resulting credentials."""
    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if not user_obj:
            print('User not found')
            return None
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        _store_credentials(user_obj, creds, db)
        return creds
    except SQLAlchemyError as e:
        db.rollback()
        print(f'DB error during OAuth: {e}')
        return None
    finally:
        db.close()


def _credentials_from_user(user: User):
    if not user.calendar_token:
        return None
    return Credentials.from_authorized_user_info(json.loads(user.calendar_token), SCOPES)


def fetch_events(user: User) -> List[dict]:
    """Fetch upcoming events from the user's primary Google Calendar."""
    creds = _credentials_from_user(user)
    if not creds:
        print('No stored OAuth token for user')
        return []
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = (
        service.events()
        .list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime')
        .execute()
    )
    return events_result.get('items', [])


def sync_user_calendar(user_id: int) -> List[dict]:
    """Fetch Google events and create matching internal events."""
    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if not user_obj:
            print('User not found')
            return []

        events = fetch_events(user_obj)
        for ev in events:
            summary = ev.get('summary', 'No Title')
            description = ev.get('description')
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            end = ev['end'].get('dateTime', ev['end'].get('date'))
            if 'T' in start:
                start = start.replace('T', ' ')[:16]
            if 'T' in end:
                end = end.replace('T', ' ')[:16]
            create_event(summary, description, start, end, linked_user_id=user_id)
        return events
    finally:
        db.close()
