from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

# Define gender enum
class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHERS = "others"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)
    is_online = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    contacts = relationship("Contact", back_populates="owner", foreign_keys="[Contact.owner_id]")


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    contact_id = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="contacts")
    contact = relationship("User", foreign_keys=[contact_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))

    content = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    media_type = Column(String, default="text")  # text, image, pdf

    # Status: sent, delivered, read
    status = Column(String, default="sent")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])