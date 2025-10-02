from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    owner = relationship("User")
    photos = relationship("Photo", back_populates="album")

    def to_dict(self, include_owner=False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_public": self.is_public,
            "user_id": self.user_id
        }
        if include_owner and self.owner:
            data["owner"] = {"id": self.owner.id, "name": self.owner.name}
        return data
