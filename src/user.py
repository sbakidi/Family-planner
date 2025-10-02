from sqlalchemy import Column, Integer, String, Table, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.database import Base

# Association Table for User-Child Many-to-Many relationship
user_child_association_table = Table('user_child_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('children.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String) # Storing hashed password
    timezone = Column(String, default="UTC")
    prefers_sse = Column(Boolean, default=True)
    prefers_email = Column(Boolean, default=False)
    calendar_token = Column(String, nullable=True)  # OAuth token for Google Calendar


    # Relationship to Shifts (One-to-Many: User has many Shifts)
    shifts = relationship("Shift", back_populates="owner")

    # Relationship to ShiftPatterns (One-to-Many: User can have many ShiftPatterns)
    shift_patterns = relationship("ShiftPattern", back_populates="owner")

    # Many-to-Many relationship with Child
    children = relationship(
        "Child",
        secondary=user_child_association_table,
        back_populates="parents"
    )

    # Relationship to ResidencyPeriods where this user is the custodian parent
    custodial_periods = relationship("ResidencyPeriod", foreign_keys="ResidencyPeriod.parent_id", backref="custodian_parent", lazy="dynamic")

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"

    def to_dict(self, include_shifts=False, include_children=False, include_custodial_periods=False, include_shift_patterns=False):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "timezone": self.timezone,
            "prefers_sse": self.prefers_sse,
            "prefers_email": self.prefers_email
        }
        if include_shifts and self.shifts:
            data['shifts'] = [shift.to_dict(include_owner=False) for shift in self.shifts]
        if include_children and self.children:
            data['children'] = [child.to_dict(include_parents=False) for child in self.children]

        if include_shift_patterns and hasattr(self, 'shift_patterns') and self.shift_patterns:
           data['shift_patterns'] = [pattern.to_dict() for pattern in self.shift_patterns]

        if include_custodial_periods and hasattr(self, 'custodial_periods') and self.custodial_periods:
            periods_to_serialize = self.custodial_periods.all() if hasattr(self.custodial_periods, 'all') else self.custodial_periods
            data['custodial_periods'] = [period.to_dict(include_parent=False) for period in periods_to_serialize]
        return data
