from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from src.database import SessionLocal
from src.album import Album
from src.photo import Photo


def add_album(name: str, description: Optional[str], user_id: Optional[int], is_public: bool = False) -> Optional[Album]:
    db = SessionLocal()
    try:
        album = Album(name=name, description=description, user_id=user_id, is_public=is_public)
        db.add(album)
        db.commit()
        db.refresh(album)
        return album
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating album: {e}")
        return None
    finally:
        db.close()


def get_albums(user_id: Optional[int] = None) -> List[Album]:
    db = SessionLocal()
    try:
        query = db.query(Album)
        if user_id is not None:
            query = query.filter(Album.user_id == user_id)
        return query.all()
    finally:
        db.close()


def add_photo(filename: str, title: Optional[str], description: Optional[str], tags: Optional[str],
              user_id: Optional[int], album_id: Optional[int], is_public: bool = False) -> Optional[Photo]:
    db = SessionLocal()
    try:
        photo = Photo(
            filename=filename,
            title=title,
            description=description,
            tags=tags,
            user_id=user_id,
            album_id=album_id,
            is_public=is_public
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        return photo
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error adding photo: {e}")
        return None
    finally:
        db.close()


def search_photos(album_id: Optional[int] = None, search: Optional[str] = None) -> List[Photo]:
    db = SessionLocal()
    try:
        query = db.query(Photo)
        if album_id is not None:
            query = query.filter(Photo.album_id == album_id)
        if search:
            like = f"%{search}%"
            query = query.filter(
                (Photo.title.ilike(like)) |
                (Photo.description.ilike(like)) |
                (Photo.tags.ilike(like))
            )
        return query.all()
    finally:
        db.close()
