from sqlalchemy.orm import Session
from sqlalchemy import desc

import models
import schemas


class UserRepo:

    async def get_or_create(db: Session, name):
        db_item = UserRepo.fetch_by_name(db, name)
        if db_item:
            return db_item
        else:
            db_item = models.User(name=name)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item

    def fetch_by_id(db: Session, _id):
        return db.query(models.User).filter(models.User.id == _id).first()

    def fetch_by_name(db: Session, name):
        return db.query(models.User).filter(models.User.name == name).first()

    def fetch_all(db: Session, skip: int = 0, limit: int = 100):
        return db.query(models.User).offset(skip).limit(limit).all()

    async def delete(db: Session, user_id):
        db_item = db.query(models.User).filter_by(id=user_id).first()
        db.delete(db_item)
        db.commit()


class MessageRepo:

    async def create(db: Session, message: schemas.Message):
        db_item = models.Message(
            body=message.body, sender_id=message.sender_id, channel_id=message.channel_id, AIComments="", suspicious=False)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    def fetch_by_id(db: Session, _id):
        return db.query(models.Message).filter(models.Message.id == _id).first()

    def fetch_by_channel(db: Session, channel_id, skip: int = 0, limit: int = 100):
        return db.query(models.Message).filter(models.Message.channel_id == channel_id).order_by(desc(models.Message.sentAt)).offset(skip).limit(limit).all()

    def fetch_all(db: Session, skip: int = 0, limit: int = 100):
        return db.query(models.Message).offset(skip).limit(limit).all()

    async def delete(db: Session, message_id):
        db_item = db.query(models.Message).filter_by(id=message_id).first()
        db.delete(db_item)
        db.commit()

    def update_ai(db: Session, msg_id: int, raw_op):
        db.query(models.Message).filter_by(id=msg_id).update({'AIComments': raw_op.get(
            "comments", ""), 'suspicious': raw_op.get("suspicious", "false") == 'true'})
        db.commit()
