from sqlalchemy import Column, Integer, String, Table, ForeignKey
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

    # Relationship to Shifts (One-to-Many: User has many Shifts)
    shifts = relationship("Shift", back_populates="owner")

    # Relationship to ShiftPatterns (One-to-Many: User can have many ShiftPatterns)
    shift_patterns = relationship("ShiftPattern", back_populates="owner")

    # Many-to-Many relationship with Child
    # 'children' attribute in User model, 'parents' attribute in Child model
    children = relationship(
        "Child",
        secondary=user_child_association_table,
        back_populates="parents"
    )

    # Relationship to ResidencyPeriods where this user is the custodian parent
    custodial_periods = relationship("ResidencyPeriod", foreign_keys="ResidencyPeriod.parent_id", backref="custodian_parent", lazy="dynamic") # Added lazy dynamic for example

    # Removed __init__ as SQLAlchemy handles it.
    # Removed shifts list, handled by SQLAlchemy relationship.
    # The previous User model had: user_id, name, email, shifts = []
    # Now it has: id, name, email, hashed_password, and relationships for shifts and children.
    # Note: The concept of user_id in auth.py (UUID hex) is different from User.id here (Integer PK).
    # This will require adjustments in how User objects are created/retrieved in auth.py and other managers.
    # Specifically, auth.register created a User object with user_id=uuid, name, email.
    # This will need to change to align with the new model.
    # For now, the focus is on the model definition.

    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', email='{self.email}')>"

    def to_dict(self, include_shifts=False, include_children=False, include_custodial_periods=False, include_shift_patterns=False): # Added include_shift_patterns
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email
            # Exclude hashed_password for security
        }
        if include_shifts and self.shifts: # Check if self.shifts is not None
            data['shifts'] = [shift.to_dict(include_owner=False) for shift in self.shifts]
        if include_children and self.children: # Check if self.children is not None
            data['children'] = [child.to_dict(include_parents=False) for child in self.children]

        if include_shift_patterns and hasattr(self, 'shift_patterns') and self.shift_patterns: # Check if self.shift_patterns is not None
           data['shift_patterns'] = [pattern.to_dict() for pattern in self.shift_patterns]

        if include_custodial_periods and hasattr(self, 'custodial_periods') and self.custodial_periods: # Check if self.custodial_periods is not None
            # If lazy='dynamic', self.custodial_periods is a query object, so use .all() or iterate
            periods_to_serialize = self.custodial_periods.all() if hasattr(self.custodial_periods, 'all') else self.custodial_periods
            data['custodial_periods'] = [period.to_dict(include_parent=False) for period in periods_to_serialize]
        return data
