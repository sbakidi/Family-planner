from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    child_id = Column(Integer, ForeignKey('children.id'), nullable=True)

    user = relationship('User')
    child = relationship('Child')

    def to_dict(self, include_user=False, include_child=False):
        data = {
            'id': self.id,
            'filename': self.filename,
            'user_id': self.user_id,
            'child_id': self.child_id
        }
        if include_user and self.user:
            data['user'] = {'id': self.user.id, 'name': self.user.name}
        if include_child and self.child:
            data['child'] = {'id': self.child.id, 'name': self.child.name}
        return data
