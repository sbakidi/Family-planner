import secrets
from functools import wraps
from flask import request, jsonify, g
from sqlalchemy.exc import SQLAlchemyError
from src.database import SessionLocal
from src.api_token import APIToken
from src.user import User


def generate_token_for_user(user_id: int):
    db = SessionLocal()
    try:
        token_value = secrets.token_hex(16)
        token = APIToken(token=token_value, user_id=user_id)
        db.add(token)
        db.commit()
        db.refresh(token)
        return token.token
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error generating token: {e}")
        return None
    finally:
        db.close()


def get_user_by_token(token_value: str):
    db = SessionLocal()
    try:
        token = db.query(APIToken).filter(APIToken.token == token_value).first()
        if token:
            return db.query(User).get(token.user_id)
        return None
    finally:
        db.close()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify(message='Authorization token required'), 401
        token_value = auth.split(' ')[1]
        user = get_user_by_token(token_value)
        if not user:
            return jsonify(message='Invalid token'), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated
