from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), nullable=False, unique=True, index=True)

    def __repr__(self):
        return 'UserMode(id=%s, name=%s)' % (self.id, self.name)


class Message(Base):
    __tablename__ = "message"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("user.id"))
    channel_id = Column(String(512), nullable=False, index=True)
    body = Column(String(4096), nullable=False, unique=False)
    AIComments = Column(String(4096), nullable=False, unique=False)
    sentAt = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return 'Store(name=%s)' % self.name


class Analysis(Base):
    __tablename__ = "analysis"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String(512), nullable=False, index=True)
    summary = Column(String(4096), nullable=False)
    last_message_id = Column(Integer)

    def __repr__(self) -> str:
        return 'Analysis(channel_id=%s)' % self.channel_id
