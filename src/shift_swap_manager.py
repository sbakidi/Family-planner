from sqlalchemy.exc import SQLAlchemyError
from src.database import SessionLocal
from src.shift_swap import ShiftSwap
from src.shift import Shift


def propose_swap(from_shift_id: int, to_shift_id: int):
    db = SessionLocal()
    try:
        new_request = ShiftSwap(from_shift_id=from_shift_id,
                                to_shift_id=to_shift_id,
                                status='pending')
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error proposing swap: {e}")
        return None
    finally:
        db.close()


def approve_swap(request_id: int):
    db = SessionLocal()
    try:
        request = db.query(ShiftSwap).filter(ShiftSwap.id == request_id).first()
        if not request or request.status != 'pending':
            return None

        from_shift = db.query(Shift).filter(Shift.id == request.from_shift_id).first()
        to_shift = db.query(Shift).filter(Shift.id == request.to_shift_id).first()
        if not from_shift or not to_shift:
            return None

        from_shift.user_id, to_shift.user_id = to_shift.user_id, from_shift.user_id
        request.status = 'approved'
        db.commit()
        db.refresh(request)
        return request
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error approving swap: {e}")
        return None
    finally:
        db.close()


def reject_swap(request_id: int):
    db = SessionLocal()
    try:
        request = db.query(ShiftSwap).filter(ShiftSwap.id == request_id).first()
        if not request or request.status != 'pending':
            return None
        request.status = 'rejected'
        db.commit()
        db.refresh(request)
        return request
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error rejecting swap: {e}")
        return None
    finally:
        db.close()
