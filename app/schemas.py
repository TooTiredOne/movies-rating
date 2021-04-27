import datetime
from typing import Optional

from pydantic import BaseModel, Field

# TODO set correct max and min lens of Fields


class MovieBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, min_length=5)
    release_year: Optional[int] = Field(
        None, gt=1900, description='Release year should be greater than 1900'
    )


class MovieCreate(MovieBase):
    pass


class Movie(MovieBase):
    id: int
    avg_rating: float

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class ReviewBase(BaseModel):
    rate: int = Field(..., ge=1, le=10)
    text: str = Field(None, min_length=5)


class ReviewCreate(ReviewBase):
    pass


class Review(ReviewBase):
    id: int
    user: User
    movie: Movie
    datetime: datetime.datetime

    class Config:
        orm_mode = True
