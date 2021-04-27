import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app import models, schemas

# from app.utils import make_query_string_for_prev_and_next_keyset_paging


# pylint: disable=too-many-arguments


def get_movie_by_title(session: Session, title: str) -> Optional[models.Movie]:
    return session.query(models.Movie).filter(models.Movie.title == title).one_or_none()


def get_movie_by_id(session: Session, movie_id: int) -> Optional[models.Movie]:
    return session.query(models.Movie).filter(models.Movie.id == movie_id).one_or_none()


def create_review(
    session: Session,
    current_user: schemas.User,
    db_movie: models.Movie,
    review: schemas.ReviewCreate,
) -> models.Review:
    db_review = models.Review(
        **review.dict(),
        movie_id=db_movie.id,
        user_id=current_user.id,
        datetime=datetime.datetime.now(),
    )
    session.add(db_review)
    session.flush()
    session.refresh(db_review)

    update_avg_rating_of_movie(session=session, db_movie=db_movie)

    return db_review


def update_avg_rating_of_movie(session: Session, db_movie: models.Movie) -> float:
    db_movie.avg_rating = calc_avg_rating(session=session, movie_id=db_movie.id)

    session.add(db_movie)
    session.flush()
    session.refresh(db_movie)

    return db_movie.avg_rating


def get_reviews(
    session: Session,
    movie_id: int,
    after_id: int = 0,
    limit: int = 20,
) -> List[models.Review]:
    reviews = (
        session.query(models.Review)
        .filter(models.Review.movie_id == movie_id)
        .filter(models.Review.id > after_id)
        .order_by(models.Review.id)
        .limit(limit)
        .all()
    )

    return reviews


def create_movie(session: Session, movie: schemas.MovieCreate) -> models.Movie:
    db_movie = models.Movie(**movie.dict())
    session.add(db_movie)
    session.flush()
    session.refresh(db_movie)

    return db_movie


def calc_avg_rating(session: Session, movie_id: int) -> float:
    avg_rating = (
        session.query(func.avg(models.Review.rate))
        .filter(models.Review.movie_id == movie_id)
        .scalar()
    )

    return 0.0 if not avg_rating else avg_rating


def calc_no_ratings(session: Session, movie_id: int) -> int:
    return session.query(models.Review).filter_by(movie_id=movie_id).count()


def calc_no_reviews(session: Session, movie_id: int) -> int:
    return (
        session.query(models.Review.text)
        .filter(models.Review.movie_id == movie_id)
        .filter(models.Review.text.isnot(None))
        .count()
    )


def get_movies(
    session: Session,
    filter_str: Optional[str] = None,
    release_year: Optional[int] = None,
    sort_by_avg_rating: bool = False,
    limit: int = 20,
    after_id: int = 0,
    before_score: int = 11,
) -> List[models.Movie]:
    db_query = session.query(models.Movie)
    if release_year:
        db_query = db_query.filter(models.Movie.release_year == release_year)
    if filter_str:
        db_query = db_query.filter(models.Movie.title.like(f'%{filter_str}%'))

    db_query = db_query.filter(models.Movie.id > after_id).filter(
        models.Movie.avg_rating < before_score
    )

    if sort_by_avg_rating:
        db_query = db_query.order_by(models.Movie.avg_rating.desc(), models.Movie.id)
    else:
        db_query = db_query.order_by(models.Movie.id)

    movies = db_query.limit(limit).all()

    return movies


def get_review_by_movie_and_user_ids(
    movie_id: int, user_id: int, session: Session
) -> Optional[models.Review]:
    return (
        session.query(models.Review)
        .filter_by(movie_id=movie_id, user_id=user_id)
        .one_or_none()
    )


def update_review(
    db_review: models.Review, new_review: schemas.ReviewCreate, session: Session
) -> schemas.Review:
    db_review.text = new_review.text
    db_review.rate = new_review.rate
    db_review.datetime = datetime.datetime.now()

    session.add(db_review)
    session.flush()
    session.refresh(db_review)

    db_movie = session.query(models.Movie).filter_by(id=db_review.movie_id).one()
    update_avg_rating_of_movie(session=session, db_movie=db_movie)

    return schemas.Review.from_orm(db_review)


def delete_movie(movie_id: int, session: Session) -> int:
    session.query(models.Movie).filter_by(id=movie_id).delete()
    session.query(models.Review).filter_by(movie_id=movie_id).delete()
    session.flush()
    return movie_id


def delete_review(movie_id: int, user_id: int, session: Session) -> None:
    session.query(models.Review).filter_by(user_id=user_id, movie_id=movie_id).delete()
    session.flush()

    db_movie = get_movie_by_id(session=session, movie_id=movie_id)
    if db_movie:
        update_avg_rating_of_movie(session=session, db_movie=db_movie)
