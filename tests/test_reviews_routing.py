import json

import pytest

from app import models, schemas

# pylint: disable=too-many-arguments
# pylint: disable=unused-argument


@pytest.mark.parametrize(
    ('movie_id', 'rate', 'text'), [(1, 5, 'average film'), (2, 9, None)]
)
def test_create_review_correct_args(
    session, auth_client, movie_id, rate, text, db_reviews, db_new_user
):
    response = auth_client.post(
        f'/movies/{movie_id}/reviews', json={'rate': rate, 'text': text}
    )

    db_new_review = (
        session.query(models.Review)
        .filter_by(user_id=db_new_user.id, movie_id=movie_id)
        .one()
    )
    expected_schema = schemas.Review.from_orm(db_new_review)

    assert response.status_code == 201
    assert session.query(models.Review).filter_by(movie_id=movie_id).count() == 3
    assert response.json() == json.loads(expected_schema.json())


@pytest.mark.parametrize(
    ('movie_id', 'rate', 'text', 'no_reviews', 'expected_code'),
    [
        (100, 10, 'some review text', 0, 404),
        ('invalid', 10, 'some text', 0, 422),
        (1, 11, 'some text', 2, 422),
        (2, -1, 'some text', 2, 422),
        (1, 'invalid', 'some text', 2, 422),
        (3, 8, '', 1, 422),
    ],
)
def test_create_review_incorrect_args(
    movie_id, rate, text, session, auth_client, expected_code, db_reviews, no_reviews
):
    response = auth_client.post(
        f'/movies/{movie_id}/reviews', json={'rate': rate, 'text': text}
    )

    assert response.status_code == expected_code
    assert (
        no_reviews == session.query(models.Review).filter_by(movie_id=movie_id).count()
    )
    assert 'detail' in response.json()


@pytest.mark.parametrize(
    ('user_id', 'movie_id', 'rate', 'text'),
    [(1, 1, 10, 'very interesting movie'), (2, 2, 5, None)],
)
def test_create_review_second_time(
    movie_id, user_id, rate, text, auth_user2, auth_user1, db_reviews
):
    cur_client = auth_user1 if user_id == 1 else auth_user2
    response = cur_client.post(
        f'/movies/{movie_id}/reviews', json={'rate': rate, 'text': text}
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Review already exists'


@pytest.mark.parametrize(
    ('movie_id', 'avg_rating', 'no_ratings', 'no_reviews', 'expected_no_reviews'),
    [(1, True, True, True, 1), (2, False, True, True, 2), (3, True, False, False, 0)],
)
def test_get_reviews_correct_args(
    movie_id,
    avg_rating,
    no_ratings,
    no_reviews,
    session,
    auth_client,
    expected_no_reviews,
    db_reviews,
):
    response = auth_client.get(
        f'/movies/{movie_id}/reviews?avg_rating={avg_rating}'
        + f'&no_ratings={no_ratings}&no_reviews={no_reviews}'
    )

    db_movie = session.query(models.Movie).filter_by(id=movie_id).one()
    db_reviews_ordered_by_movie_id = (
        session.query(models.Review)
        .filter_by(movie_id=movie_id)
        .order_by(models.Review.id)
        .all()
    )
    expected_response = dict()
    if avg_rating:
        expected_response['avg_rating'] = db_movie.avg_rating
    if no_ratings:
        expected_response['no_ratings'] = len(db_movie.reviews)
    if no_reviews:
        expected_response['no_reviews'] = expected_no_reviews

    expected_response['reviews'] = []
    for review in db_reviews_ordered_by_movie_id:
        json_str = schemas.Review.from_orm(review).json()
        expected_response['reviews'].append(json.loads(json_str))

    assert response.status_code == 200
    assert response.json() == expected_response


@pytest.mark.parametrize(
    (
        'movie_id',
        'limit',
        'after_id',
        'avg_rating',
        'no_ratings',
        'no_reviews',
        'expected_code',
    ),
    [
        (100, 20, 0, False, False, False, 404),
        ('invalid', 20, 0, False, False, False, 422),
        (1, -1, 0, False, False, False, 422),
        (1, 'invalid', 0, False, False, False, 422),
        (1, None, 'invalid string', False, False, False, 422),
        (1, None, 0, 'invalid string', False, False, 422),
        (1, None, 0, False, 'invalid string', False, 422),
        (1, None, 0, False, False, 'invalid string', 422),
    ],
)
def test_get_reviews_incorrect_args(
    session,
    auth_client,
    movie_id,
    limit,
    after_id,
    avg_rating,
    no_ratings,
    no_reviews,
    db_reviews,
    expected_code,
):
    response = auth_client.get(
        f'/movies/{movie_id}/reviews?limit={limit}&after_id={after_id}'
        + f'&avg_rating={avg_rating}&no_ratings={no_ratings}&no_reviews={no_reviews}'
    )

    assert response.status_code == expected_code
    assert 'detail' in response.json()


@pytest.mark.parametrize(
    (
        'movie_id',
        'user_id',
        'expected_avg_rating',
        'initial_movie_review_count',
        'initial_user_review_count',
    ),
    [(1, 1, 2, 2, 3), (2, 2, 2, 2, 2), (3, 1, 0, 1, 3)],
)
def test_delete_review_correct_args(
    session,
    auth_user1,
    auth_user2,
    movie_id,
    user_id,
    expected_avg_rating,
    db_reviews,
    db_movies,
    initial_movie_review_count,
    initial_user_review_count,
):
    cur_client = auth_user1 if user_id == 1 else auth_user2
    response = cur_client.delete(f'/movies/{movie_id}/reviews')

    movie_review_count_after_request = (
        session.query(models.Review).filter_by(movie_id=movie_id).count()
    )
    user_review_count_after_request = (
        session.query(models.Review).filter_by(user_id=user_id).count()
    )
    db_movie = session.query(models.Movie).filter_by(id=movie_id).one()

    assert response.status_code == 200
    assert movie_review_count_after_request + 1 == initial_movie_review_count
    assert user_review_count_after_request + 1 == initial_user_review_count
    assert db_movie.avg_rating == expected_avg_rating
    assert response.json()


@pytest.mark.parametrize(
    (
        'movie_id',
        'user_id',
        'initial_movie_review_count',
        'initial_user_review_count',
        'expected_code',
    ),
    [
        (100, 1, 0, 3, 404),
        ('invalid', 2, 0, 2, 422),
    ],
)
def test_delete_review_incorrect_args(
    session,
    auth_user1,
    auth_user2,
    movie_id,
    user_id,
    db_reviews,
    initial_user_review_count,
    initial_movie_review_count,
    expected_code,
):
    cur_client = auth_user1 if user_id == 1 else auth_user2
    response = cur_client.delete(f'/movies/{movie_id}/reviews')

    movie_review_count_after_request = (
        session.query(models.Review).filter_by(movie_id=movie_id).count()
    )
    user_review_count_after_request = (
        session.query(models.Review).filter_by(user_id=user_id).count()
    )

    assert response.status_code == expected_code
    assert movie_review_count_after_request == initial_movie_review_count
    assert user_review_count_after_request == initial_user_review_count
    assert 'detail' in response.json()
