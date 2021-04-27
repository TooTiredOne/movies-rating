import os
from datetime import datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models
from app.api import app as fastapi_app
from app.database import DeclarativeBase
from app.dependencies import get_session
from app.utils import make_password_hash

# pylint: disable=unused-argument

SQLALCHEMY_DATABASE_URL = 'sqlite:///./test.db'
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={'check_same_thread': False}
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_session() -> Generator[Session, None, None]:
    session = TestingSession()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


fastapi_app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name='app')
def _app():
    try:
        DeclarativeBase.metadata.create_all(bind=engine)
        yield fastapi_app
    except Exception as e:
        raise e
    finally:
        os.unlink('./test.db')


@pytest.fixture(name='session')
def _session(app) -> Session:
    cur_session = TestingSession()
    try:
        yield cur_session
    except Exception as e:
        raise e
    finally:
        cur_session.close()


@pytest.fixture(name='db_users')
def _db_users(session):
    user1 = models.User(
        username='username1', hashed_password=make_password_hash('password1')
    )
    user2 = models.User(
        username='username2', hashed_password=make_password_hash('password2')
    )

    session.add(user1)
    session.add(user2)
    session.commit()

    return user1, user2


@pytest.fixture(name='db_movies')
def _db_movies(session):
    movie1 = models.Movie(title='title1', description='description1', release_year=2018)
    movie2 = models.Movie(title='title2', description='description2', release_year=2018)
    movie3 = models.Movie(title='title3', description='description3', release_year=2020)
    movie1.avg_rating = 6
    movie2.avg_rating = 3
    movie3.avg_rating = 7

    session.add(movie1)
    session.add(movie2)
    session.add(movie3)
    session.commit()

    return movie1, movie2, movie3


@pytest.fixture(name='db_user1_reviews')
def _db_user1_reviews(db_users, db_movies, session):
    user1, _ = db_users
    movie1, movie2, movie3 = db_movies

    review_movie1 = models.Review(
        user=user1, movie=movie1, rate=10, text='very good', datetime=datetime.now()
    )
    review_movie2 = models.Review(
        user=user1, movie=movie2, rate=2, text='boring', datetime=datetime.now()
    )
    review_movie3 = models.Review(
        user=user1, movie=movie3, rate=7, datetime=datetime.now()
    )

    session.add(review_movie1)
    session.add(review_movie2)
    session.add(review_movie3)
    session.commit()

    return review_movie1, review_movie2, review_movie3


@pytest.fixture(name='db_user2_reviews')
def _db_user2_reviews(db_users, db_movies, session):
    _, user2 = db_users
    movie1, movie2, _ = db_movies

    review_movie1 = models.Review(
        user=user2, movie=movie1, rate=2, datetime=datetime.now()
    )

    review_movie2 = models.Review(
        user=user2, movie=movie2, rate=4, text='average', datetime=datetime.now()
    )

    session.add(review_movie1)
    session.add(review_movie2)
    session.commit()

    return review_movie1, review_movie2


@pytest.fixture()
def db_reviews(db_user1_reviews, db_user2_reviews):
    return db_user1_reviews, db_user2_reviews


@pytest.fixture(name='db_new_user')
def _db_new_user(session, db_users):
    username = 'new_user'
    password = 'password'

    new_user = models.User(
        username=username, hashed_password=make_password_hash(password)
    )
    session.add(new_user)
    session.commit()

    return new_user


@pytest.fixture()
def auth_client(app, db_new_user) -> TestClient:
    cur_client = TestClient(app)
    cur_client.auth = ('new_user', 'password')
    return cur_client


@pytest.fixture()
def auth_user1(app, db_users):
    user1_client = TestClient(app)
    user1_client.auth = ('username1', 'password1')
    return user1_client


@pytest.fixture()
def auth_user2(app, db_users):
    user2_client = TestClient(app)
    user2_client.auth = ('username2', 'password2')
    return user2_client


@pytest.fixture()
def unauth_client(app) -> TestClient:
    return TestClient(app)
