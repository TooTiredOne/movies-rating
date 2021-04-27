from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud_movies as crud
from .. import models, schemas
from ..dependencies import get_current_user, get_session

router = APIRouter()


# pylint: disable=too-many-arguments


class ReviewNotFound(HTTPException):
    def __init__(self, **kwargs: Dict[Any, Any]):
        super().__init__(status_code=404, detail='Review not found', **kwargs)


class MovieNotFound(HTTPException):
    def __init__(self, **kwargs: Dict[Any, Any]):
        super().__init__(status_code=404, detail='Movie not found', **kwargs)


@router.post(
    '',
    response_model=schemas.Movie,
    status_code=status.HTTP_201_CREATED,
    tags=['movies'],
    summary='Create new movie',
    dependencies=[Depends(get_current_user)],
)
def create_movie(
    movie: schemas.MovieCreate, session: Session = Depends(get_session)
) -> Optional[models.Movie]:
    return crud.create_movie(session=session, movie=movie)


@router.post(
    '/{movie_id}/reviews',
    response_model=schemas.Review,
    status_code=status.HTTP_201_CREATED,
    tags=['movies', 'reviews'],
    summary='Create new review for given movie',
)
def create_review(
    movie_id: int,
    review: schemas.ReviewCreate,
    session: Session = Depends(get_session),
    current_user: schemas.User = Depends(get_current_user),
) -> Optional[models.Review]:
    db_movie = crud.get_movie_by_id(session=session, movie_id=movie_id)
    if not db_movie:
        raise MovieNotFound

    db_review = crud.get_review_by_movie_and_user_ids(
        movie_id=movie_id, user_id=current_user.id, session=session
    )
    if db_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Review already exists'
        )

    try:
        return crud.create_review(
            session=session, current_user=current_user, db_movie=db_movie, review=review
        )
    except IntegrityError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='User has already rated this movie',
        ) from err


@router.put(
    '/{movie_id}/reviews',
    response_model=schemas.Review,
    tags=['movies', 'reviews'],
    summary='Update review of authorized user',
)
def update_review(
    movie_id: int,
    review: schemas.ReviewCreate,
    session: Session = Depends(get_session),
    current_user: schemas.User = Depends(get_current_user),
) -> Optional[schemas.Review]:
    db_review = crud.get_review_by_movie_and_user_ids(
        session=session, movie_id=movie_id, user_id=current_user.id
    )
    if not db_review:
        raise ReviewNotFound

    return crud.update_review(db_review=db_review, new_review=review, session=session)


@router.delete(
    '/{movie_id}/reviews', tags=['reviews'], summary='Delete review of authorized user'
)
def delete_review(
    movie_id: int,
    session: Session = Depends(get_session),
    current_user: schemas.User = Depends(get_current_user),
) -> Optional[int]:
    db_review = crud.get_review_by_movie_and_user_ids(
        session=session, movie_id=movie_id, user_id=current_user.id
    )
    if not db_review:
        raise ReviewNotFound

    review_id = db_review.id
    crud.delete_review(session=session, movie_id=movie_id, user_id=current_user.id)
    return review_id


@router.get(
    '/{movie_id}/reviews',
    tags=['movies', 'reviews'],
    response_model=Dict[str, Union[List[schemas.Review], float]],
    summary='Get reviews of given movie',
    dependencies=[Depends(get_current_user)],
)
def get_reviews(
    movie_id: int,
    after_id: int = 0,
    limit: int = Query(20, gt=0),
    avg_rating: bool = False,
    no_ratings: bool = False,
    no_reviews: bool = False,
    session: Session = Depends(get_session),
) -> Dict[str, Union[List[models.Review], float]]:
    db_movie = crud.get_movie_by_id(session=session, movie_id=movie_id)
    if not db_movie:
        raise MovieNotFound

    response = dict()
    if avg_rating:
        response['avg_rating'] = db_movie.avg_rating
    if no_ratings:
        response['no_ratings'] = crud.calc_no_ratings(
            session=session, movie_id=movie_id
        )
    if no_reviews:
        response['no_reviews'] = crud.calc_no_reviews(
            session=session, movie_id=movie_id
        )

    reviews = crud.get_reviews(
        movie_id=movie_id,
        session=session,
        after_id=after_id,
        limit=limit,
    )

    response['reviews'] = reviews

    return response


@router.get(
    '',
    tags=['movies'],
    response_model=List[schemas.Movie],
    summary='Get a list of movies',
    dependencies=[Depends(get_current_user)],
)
def get_movies(
    after_id: int = 0,
    before_score: int = 11,
    limit: int = Query(20, gt=0),
    session: Session = Depends(get_session),
    filter_str: Optional[str] = None,
    release_year: Optional[int] = None,
    sort_by_avg_rating: bool = False,
) -> List[models.Movie]:
    movies = crud.get_movies(
        session=session,
        filter_str=filter_str,
        release_year=release_year,
        sort_by_avg_rating=sort_by_avg_rating,
        limit=limit,
        after_id=after_id,
        before_score=before_score,
    )

    return movies


@router.delete(
    '/{movie_id}',
    tags=['movies'],
    summary='Delete Movie',
    dependencies=[Depends(get_current_user)],
)
def delete_movie(
    movie_id: int, session: Session = Depends(get_session)
) -> Optional[int]:
    db_movie = crud.get_movie_by_id(session=session, movie_id=movie_id)
    if not db_movie:
        raise MovieNotFound

    return crud.delete_movie(session=session, movie_id=movie_id)
