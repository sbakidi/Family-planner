from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True)
    filename = Column(String)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    album_id = Column(Integer, ForeignKey('albums.id'), nullable=True)

    owner = relationship("User")
    album = relationship("Album", back_populates="photos")

    def to_dict(self, include_owner=False, include_album=False):
        data = {
            "id": self.id,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "is_public": self.is_public,
            "user_id": self.user_id,
            "album_id": self.album_id
        }
        if include_owner and self.owner:
            data["owner"] = {"id": self.owner.id, "name": self.owner.name}
        if include_album and self.album:
            data["album"] = {"id": self.album.id, "name": self.album.name}
        return data
