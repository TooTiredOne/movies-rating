import json

import pytest

from app import models, schemas
from app.utils import make_password_hash

# pylint: disable=unused-argument
# pylint: disable=too-many-arguments


def test_registration(unauth_client, session, db_users):
    response = unauth_client.post(
        '/users', json={'username': 'new_user', 'password': 'pass'}
    )
    users = session.query(models.User).all()
    new_user = session.query(models.User).filter_by(username='new_user').one()

    assert response.status_code == 201
    assert response.json()['username'] == 'new_user'
    assert new_user.hashed_password == make_password_hash('pass')
    assert len(users) == len(db_users) + 1


def test_registration_existing_username(unauth_client, session, db_users):
    response = unauth_client.post(
        '/users', json={'username': 'username1', 'password': 'pass'}
    )

    users = session.query(models.User).all()

    assert response.status_code == 409
    assert response.json() == {'detail': 'Username already taken'}
    assert len(users) == len(db_users)


@pytest.mark.parametrize(('limit', 'after_id'), [(20, 0), (1, 0), (1, 1), (1, 2)])
def test_get_all_users(session, auth_client, limit, after_id, db_users):
    # new_user, auth = new_user_and_auth_head

    response = auth_client.get(f'/users?limit={limit}&after_id={after_id}')
    data = response.json()

    expected_users = set(
        (db_user.username, db_user.id)
        for db_user in session.query(models.User)
        .filter(models.User.id > after_id)
        .order_by(models.User.id)
        .limit(limit)
        .all()
    )
    obtained_users = set((user['username'], user['id']) for user in data)

    assert response.status_code == 200
    assert expected_users == obtained_users


@pytest.mark.parametrize(('limit', 'after_id'), [(0, 0), (3, 'invalid')])
def test_get_all_users_incorrect_args(auth_client, limit, after_id, db_users):
    response = auth_client.get(f'/users?limit={limit}&after_id={after_id}')

    assert response.status_code == 422
    assert 'detail' in response.json()


@pytest.mark.parametrize(('user_id', 'movie_id'), [(1, 2), (2, 2), (1, 3)])
def test_get_user_review_on_movie_correct_args(
    user_id, movie_id, auth_client, session, db_user1_reviews, db_user2_reviews
):
    response = auth_client.get(f'/users/{user_id}/reviews/movies/{movie_id}')
    expected_review = (
        db_user1_reviews[movie_id - 1]
        if user_id == 1
        else db_user2_reviews[movie_id - 1]
    )
    expected_schema = (
        schemas.Review.from_orm(expected_review) if expected_review else None
    )

    assert response.status_code == 200
    if expected_schema:
        assert response.json() == json.loads(expected_schema.json())
    else:
        assert not response.json()


@pytest.mark.parametrize(
    ('user_id', 'movie_id'),
    [(100, 1), (1, 100), ('invalid string', 2), (2, 'invalid string')],
)
def test_get_user_review_on_movie_incorrect_args(
    user_id, movie_id, auth_client, db_reviews
):
    response = auth_client.get(f'/users/{user_id}/reviews/movies/{movie_id}')

    if user_id == 'invalid string' or movie_id == 'invalid string':
        assert response.status_code == 422
    else:
        assert response.status_code == 404
    assert 'detail' in response.json()


@pytest.mark.parametrize(
    'user_id',
    [
        1,
        2,
    ],
)
def test_get_user_reviews_correct_args(
    user_id, session, auth_client, db_user1_reviews, db_user2_reviews
):
    response = auth_client.get(f'/users/{user_id}/reviews')
    data = response.json()
    reviews = db_user1_reviews if user_id == 1 else db_user2_reviews
    expected_reviews = []
    for review in reviews:
        json_str = schemas.Review.from_orm(review).json()
        expected_reviews.append(json.loads(json_str))

    assert response.status_code == 200
    assert data == expected_reviews


@pytest.mark.parametrize(
    ('user_id', 'limit', 'after_id', 'expected_code'),
    [
        (100, 20, 0, 404),
        ('invalid string', 20, 0, 422),
        (1, 0, None, 422),
        (1, 'invalid string', 0, 422),
        (1, 3, 'incorrect bookmark', 422),
    ],
)
def test_get_user_reviews_incorrect_args(
    user_id, limit, after_id, session, auth_client, db_reviews, expected_code
):
    response = auth_client.get(
        f'/users/{user_id}/reviews?limit={limit}&after_id={after_id}'
    )

    assert response.status_code == expected_code
    assert 'detail' in response.json()
