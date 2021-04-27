from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud_users as crud
from .. import models, schemas
from ..dependencies import get_current_user, get_session

router = APIRouter()


class UsernameAlreadyTaken(HTTPException):
    def __init__(self, **kwargs: Dict[Any, Any]):
        super().__init__(status_code=409, detail='Username already taken', **kwargs)


@router.post(
    '',
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED,
    summary='Register new user',
)
def create_user(
    user: schemas.UserCreate, session: Session = Depends(get_session)
) -> models.User:
    db_user = crud.get_user_by_username(session, username=user.username)
    if db_user:
        raise UsernameAlreadyTaken
    try:  # to catch racing condition
        return crud.create_user(session, user)
    except IntegrityError as err:
        raise UsernameAlreadyTaken from err


@router.get(
    '',
    tags=['users'],
    response_model=List[schemas.User],
    summary='Get all users',
    dependencies=[Depends(get_current_user)],
)
def get_all_users(
    after_id: int = 0,
    limit: int = Query(20, gt=0),
    session: Session = Depends(get_session),
) -> List[models.User]:
    return crud.get_all_users(session=session, after_id=after_id, limit=limit)


@router.get(
    '/{user_id}/reviews/movies/{movie_id}',
    response_model=schemas.Review,
    tags=['reviews', 'movies'],
    summary='Get review of a user to given movie',
    dependencies=[Depends(get_current_user)],
)
def get_user_review_on_movie(
    user_id: int, movie_id: int, session: Session = Depends(get_session)
) -> Optional[models.Review]:
    db_review = crud.get_user_review_on_movie(
        user_id=user_id, movie_id=movie_id, session=session
    )

    if not db_review:
        raise HTTPException(status_code=404, detail='Review not found')

    return db_review


@router.get(
    '/{user_id}/reviews',
    response_model=List[schemas.Review],
    tags=['users', 'reviews'],
    summary='Get reviews of user with given id',
    dependencies=[Depends(get_current_user)],
)
def get_user_reviews(
    user_id: int,
    after_id: int = 0,
    limit: int = Query(20, gt=0),
    session: Session = Depends(get_session),
) -> List[models.Review]:
    db_user = crud.get_user_by_id(session=session, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')

    reviews = crud.get_user_reviews(
        user_id=user_id, session=session, after_id=after_id, limit=limit
    )

    return reviews
