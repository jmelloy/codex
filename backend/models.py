from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from database import Base

image_tags = Table(
    "image_tags",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("images.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, unique=True, nullable=False)
    directory = Column(String, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)
    date_taken = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rating = Column(Integer, default=0)  # -1=thumbs down, 0=unrated, 1=thumbs up, 2-5=stars
    hidden = Column(Boolean, default=False)
    sidecar_data = Column(Text, nullable=True)   # raw JSON as text
    prompt = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    tags = relationship("Tag", secondary=image_tags, back_populates="images")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)

    images = relationship("Image", secondary=image_tags, back_populates="tags")
