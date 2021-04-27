from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates

from .database import DeclarativeBase

# pylint: disable=line-too-long


class User(DeclarativeBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    reviews = relationship(
        'Review', back_populates='user', cascade='all, delete', passive_deletes=True
    )

    def __repr__(self) -> str:
        return f'username: {self.username}, id: {self.id}'


class Movie(DeclarativeBase):
    __tablename__ = 'movies'
    __table_args__ = (CheckConstraint('release_year > 1900'),)

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    release_year = Column(Integer)
    avg_rating = Column(Float, default=0.0, nullable=False)

    reviews = relationship(
        'Review', back_populates='movie', cascade='all, delete', passive_deletes=True
    )

    @validates('title')
    def validate_title(self, _: Any, value: str) -> str:
        if not value:
            raise ValueError('movie must have a title')
        return value

    @validates('description')
    def validate_description(self, _: Any, value: str) -> str:
        if value and len(value) < 5:
            raise ValueError('description should be at least 5 characters')
        return value

    def __repr__(self) -> str:
        return f'title: {self.title}, release_year: {self.release_year}'


class Review(DeclarativeBase):
    __tablename__ = 'reviews'
    __table_args__ = (
        CheckConstraint('rate >= 0 AND rate <= 10'),
        UniqueConstraint('user_id', 'movie_id'),
    )

    id = Column(Integer, primary_key=True)
    rate = Column(Integer, nullable=False)
    text = Column(String)
    datetime = Column(DateTime, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    movie_id = Column(Integer, ForeignKey('movies.id', ondelete='CASCADE'))

    user = relationship('User', back_populates='reviews', uselist=False)
    movie = relationship('Movie', back_populates='reviews', uselist=False)

    @validates('text')
    def validate_text(self, _: Any, value: str) -> str:
        if value and len(value) < 5:
            raise ValueError('text should be at least 5 characters')
        return value

    def __repr__(self) -> str:
        return f'user_id: {self.user_id}, movie_id: {self.movie_id}, rate: {self.rate}, text: {self.text}'
