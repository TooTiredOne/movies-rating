from typing import List, Optional

from sqlalchemy.orm import Session

from app import models, schemas
from app.utils import make_password_hash


def get_user_by_id(session: Session, user_id: int) -> Optional[models.User]:
    return session.query(models.User).filter(models.User.id == user_id).one_or_none()


def get_user_by_username(session: Session, username: str) -> Optional[models.User]:
    return (
        session.query(models.User)
        .filter(models.User.username == username)
        .one_or_none()
    )


def get_all_users(
    session: Session, after_id: int = 0, limit: int = 20
) -> List[models.User]:
    users = (
        session.query(models.User)
        .filter(models.User.id > after_id)
        .order_by(models.User.id)
        .limit(limit)
        .all()
    )
    return users


def get_user_reviews(
    user_id: int, session: Session, after_id: int = 0, limit: int = 20
) -> List[models.Review]:
    reviews = (
        session.query(models.Review)
        .filter_by(user_id=user_id)
        .filter(models.Review.id > after_id)
        .order_by(models.Review.id)
        .limit(limit)
        .all()
    )

    return reviews


def get_user_review_on_movie(
    user_id: int, movie_id: int, session: Session
) -> Optional[models.Review]:
    return (
        session.query(models.Review)
        .filter_by(user_id=user_id, movie_id=movie_id)
        .one_or_none()
    )


def create_user(session: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = make_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    session.add(db_user)
    session.flush()
    return db_user
