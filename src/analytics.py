from sqlalchemy import func
from .database import SessionLocal
from .shift import Shift
from .event import Event
from .residency_period import ResidencyPeriod


def get_monthly_analytics(user_id: int):
    """Return monthly counts of shifts, events and residency periods for a user."""
    db = SessionLocal()
    try:
        shift_counts = db.query(
            func.strftime('%Y-%m', Shift.start_time).label('month'),
            func.count(Shift.id)
        ).filter(Shift.user_id == user_id).group_by('month').all()

        event_counts = db.query(
            func.strftime('%Y-%m', Event.start_time).label('month'),
            func.count(Event.id)
        ).filter(Event.user_id == user_id).group_by('month').all()

        residency_counts = db.query(
            func.strftime('%Y-%m', ResidencyPeriod.start_datetime).label('month'),
            func.count(ResidencyPeriod.id)
        ).filter(ResidencyPeriod.parent_id == user_id).group_by('month').all()

        data = {
            'shifts': [{'month': m, 'count': c} for m, c in shift_counts],
            'events': [{'month': m, 'count': c} for m, c in event_counts],
            'residency_periods': [{'month': m, 'count': c} for m, c in residency_counts]
        }
        return data
    finally:
        db.close()


def export_monthly_analytics_csv(user_id: int, file_path: str):
    """Export analytics data to a CSV file."""
    import csv
    data = get_monthly_analytics(user_id)

    months = set()
    for category in data.values():
        months.update(item['month'] for item in category)
    months = sorted(months)

    shift_map = {d['month']: d['count'] for d in data['shifts']}
    event_map = {d['month']: d['count'] for d in data['events']}
    res_map = {d['month']: d['count'] for d in data['residency_periods']}

    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['month', 'shifts', 'events', 'residency_periods'])
        for month in months:
            writer.writerow([
                month,
                shift_map.get(month, 0),
                event_map.get(month, 0),
                res_map.get(month, 0)
            ])

