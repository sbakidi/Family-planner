from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.exc import SQLAlchemyError

from .database import Base, SessionLocal

class Badge(Base):
    """Model tracking a user's points and earned badges."""

    __tablename__ = "badges"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    points = Column(Integer, default=0)
    badges = Column(String, default="")

    user = relationship("User")

    def __repr__(self):
        return f"<Badge(user_id={self.user_id}, points={self.points}, badges='{self.badges}')>"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "points": self.points,
            "badges": self.badges.split(",") if self.badges else []
        }


def award_points(user_id: int, points: int, badge_name: str | None = None):
    """Increment points for a user and optionally record a badge name."""
    db = SessionLocal()
    try:
        badge = db.query(Badge).filter(Badge.user_id == user_id).first()
        if not badge:
            badge = Badge(user_id=user_id, points=0, badges="")
            db.add(badge)

        badge.points += points
        if badge_name:
            existing = badge.badges.split(",") if badge.badges else []
            if badge_name not in existing:
                existing.append(badge_name)
                badge.badges = ",".join(existing)

        db.commit()
        db.refresh(badge)
        return badge
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error awarding points: {e}")
        return None
    finally:
        db.close()
