from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum


# Enum for representing user gender
# Stored as string values in DB
class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHERS = "others"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Hashed password
    display_name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)

    # Used to track real-time presence
    is_online = Column(Boolean, default=False)

    # Automatically set when user is created
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # One-to-many relationship:
    # A user can have multiple contacts
    contacts = relationship(
        "Contact",
        back_populates="owner",
        foreign_keys="[Contact.owner_id]",
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)

    # Owner of the contact list
    owner_id = Column(Integer, ForeignKey("users.id"))

    # The user added as a contact
    contact_id = Column(Integer, ForeignKey("users.id"))

    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to the owning user
    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="contacts",
    )

    # Relationship to the contact user
    contact = relationship("User", foreign_keys=[contact_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))

    # Original message content
    content = Column(Text, nullable=True)

    # Translation-related fields
    original_language = Column(String, nullable=True)
    translated_content = Column(Text, nullable=True)
    is_translated = Column(Boolean, default=False)

    # Media handling (image, pdf, etc.)
    media_url = Column(String, nullable=True)
    media_type = Column(String, default="text")  # text | image | pdf

    # Message lifecycle status
    status = Column(String, default="sent")  # sent | delivered | read

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships for sender and receiver
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class ChatPreference(Base):
    __tablename__ = "chat_preferences"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    friend_id = Column(Integer, ForeignKey("users.id"))

    # Preferred language for translation with this friend
    preferred_language = Column(String, default="en")

    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])
