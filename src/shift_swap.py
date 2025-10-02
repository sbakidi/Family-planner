from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class ShiftSwap(Base):
    __tablename__ = 'shift_swaps'

    id = Column(Integer, primary_key=True, index=True)
    from_shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    to_shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    status = Column(String, default='pending')

    from_shift = relationship('Shift', foreign_keys=[from_shift_id])
    to_shift = relationship('Shift', foreign_keys=[to_shift_id])

    def to_dict(self):
        return {
            'id': self.id,
            'from_shift_id': self.from_shift_id,
            'to_shift_id': self.to_shift_id,
            'status': self.status
        }
