from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from src.database import SessionLocal
from src.booking import Booking
from src import event_manager


def _parse_datetime(dt_str: str):
    if not dt_str:
        return None
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print(f"Warning: Could not parse datetime string: {dt_str}")
        return None


def create_booking(service: str, start_time_str: str, end_time_str: str, user_id: int):
    db = SessionLocal()
    try:
        start_dt = _parse_datetime(start_time_str)
        end_dt = _parse_datetime(end_time_str)
        if not start_dt or not end_dt:
            print("Error: Invalid start or end time format for booking.")
            return None
        booking = Booking(service=service, start_time=start_dt, end_time=end_dt, user_id=user_id)
        db.add(booking)
        db.commit()
        db.refresh(booking)

        event = event_manager.create_event(
            title=f"Booking: {service}",
            description=f"Service booking for {service}",
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            linked_user_id=user_id,
            linked_child_id=None,
        )
        if event:
            booking.event_id = event.id
            db.commit()
            db.refresh(booking)
        return booking
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating booking: {e}")
        return None
    finally:
        db.close()


def get_booking_details(booking_id: int):
    db = SessionLocal()
    try:
        return db.query(Booking).filter(Booking.id == booking_id).first()
    except SQLAlchemyError as e:
        print(f"Database error getting booking details: {e}")
        return None
    finally:
        db.close()


def get_bookings_for_user(user_id: int):
    db = SessionLocal()
    try:
        return db.query(Booking).filter(Booking.user_id == user_id).all()
    except SQLAlchemyError as e:
        print(f"Database error getting bookings for user: {e}")
        return []
    finally:
        db.close()


def update_booking(booking_id: int, service: str = None, start_time_str: str = None, end_time_str: str = None):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            print("Error: Booking not found.")
            return None
        updated = False
        if service is not None:
            booking.service = service
            updated = True
        if start_time_str is not None:
            st = _parse_datetime(start_time_str)
            if st:
                booking.start_time = st
                updated = True
        if end_time_str is not None:
            et = _parse_datetime(end_time_str)
            if et:
                booking.end_time = et
                updated = True
        if updated:
            db.commit()
            db.refresh(booking)
            if booking.event_id:
                event_manager.update_event(
                    booking.event_id,
                    title=f"Booking: {booking.service}",
                    start_time_str=start_time_str or booking.start_time.strftime("%Y-%m-%d %H:%M"),
                    end_time_str=end_time_str or booking.end_time.strftime("%Y-%m-%d %H:%M"),
                )
        return booking
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error updating booking: {e}")
        return None
    finally:
        db.close()


def delete_booking(booking_id: int):
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            print("Error: Booking not found for deletion.")
            return False
        if booking.event_id:
            event_manager.delete_event(booking.event_id)
        db.delete(booking)
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error deleting booking: {e}")
        return False
    finally:
        db.close()
