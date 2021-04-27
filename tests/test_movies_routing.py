import pytest

from app import models, schemas

# pylint: disable=too-many-arguments
# pylint: disable=unused-argument


@pytest.mark.parametrize(
    ('title', 'description', 'release_year'),
    [
        ('new title', 'some cool description', 2018),
        ('new title', None, 1975),
        ('new title', 'some cool description', None),
        ('new title', None, None),
    ],
)
def test_create_movie_correct_args(
    title, description, release_year, session, auth_client, db_movies
):
    response = auth_client.post(
        '/movies',
        json={'title': title, 'description': description, 'release_year': release_year},
    )
    data = response.json()

    db_new_movie = session.query(models.Movie).filter_by(title=title).one()

    assert response.status_code == 201
    assert len(db_movies) + 1 == session.query(models.Movie).count()
    assert db_new_movie.description == description
    assert db_new_movie.release_year == release_year
    assert data == schemas.Movie.from_orm(db_new_movie)


@pytest.mark.parametrize(
    ('title', 'description', 'release_year'),
    [
        (None, 'some description', 2018),
        ('new title', 'some description', 1800),
        ('new title', None, 'invalid string'),
    ],
)
def test_create_movie_incorrect_args(
    title, description, release_year, session, auth_client, db_movies
):

    response = auth_client.post(
        '/movies',
        json={'title': title, 'description': description, 'release_year': release_year},
    )

    assert response.status_code == 422
    assert 'detail' in response.json()
    assert len(db_movies) == session.query(models.Movie).count()


@pytest.mark.parametrize(
    (
        'limit',
        'after_id',
        'before_score',
        'filter_str',
        'release_year',
        'sort_by_avg_rating',
        'expected_titles',
    ),
    [
        (20, 0, 11, '1', None, False, ['title1']),
        (20, 0, 11, '2', None, False, ['title2']),
        (20, 0, 11, '3', None, False, ['title3']),
        (20, 0, 11, None, 2018, True, ['title1', 'title2']),
        (20, 0, 11, None, 2020, True, ['title3']),
        (20, 0, 11, None, 2021, True, []),
        (20, 0, 11, '1', 2018, True, ['title1']),
        (20, 0, 11, 'no match', None, False, []),
        (20, 0, 11, None, None, True, ['title3', 'title1', 'title2']),
        (1, 0, 7, None, None, True, ['title1']),
        (1, 0, 6, None, None, True, ['title2']),
    ],
)
def test_get_movies_correct_args(
    auth_client,
    db_movies,
    filter_str,
    release_year,
    sort_by_avg_rating,
    expected_titles,
    limit,
    after_id,
    before_score,
):
    query_string = f'?after_id={after_id}&before_score={before_score}&limit={limit}&'
    if sort_by_avg_rating:
        query_string += f'sort_by_avg_rating={sort_by_avg_rating}&'
    if filter_str:
        query_string += f'filter_str={filter_str}&'
    if release_year:
        query_string += f'release_year={release_year}&'

    response = auth_client.get('/movies' + query_string)

    assert response.status_code == 200
    assert [movie['title'] for movie in response.json()] == expected_titles


@pytest.mark.parametrize(
    ('limit', 'before_score', 'after_id', 'release_year', 'sort_by_avg_rating'),
    [
        (0, 11, None, 2018, False),
        ('invalid', 11, 0, 2018, False),
        (1, 11, 'invalid', 2018, False),
        (1, 11, 0, 'invalid', False),
        (1, 11, 0, 2018, 'invalid'),
        (1, 'invalid', 0, 2018, False),
    ],
)
def test_get_movies_incorrect_args(
    auth_client,
    limit,
    after_id,
    release_year,
    sort_by_avg_rating,
    before_score,
    db_movies,
):
    response = auth_client.get(
        f'/movies?limit={limit}&after_id={after_id}&before_score={before_score}'
        + f'&release_year={release_year}&sort_by_avg_rating={sort_by_avg_rating}'
    )

    assert response.status_code == 422
    assert 'detail' in response.json()


@pytest.mark.parametrize(
    ('movie_id', 'user_id', 'rate', 'text'),
    [
        (1, 1, 8, 'it has some potential'),
        (2, 2, 2, 'need more explosions'),
        (3, 1, 8, None),
    ],
)
def test_update_movie_review_correct_args(
    movie_id, user_id, rate, text, session, auth_user1, auth_user2, db_reviews
):
    cur_client = auth_user1 if user_id == 1 else auth_user2
    response = cur_client.put(
        f'/movies/{movie_id}/reviews', json={'rate': rate, 'text': text}
    )
    data = response.json()

    db_review = (
        session.query(models.Review).filter_by(user_id=user_id, movie_id=movie_id).one()
    )

    assert response.status_code == 200
    assert data['rate'] == rate
    assert data['text'] == text
    assert db_review.rate == rate
    assert db_review.text == text


@pytest.mark.parametrize(
    ('movie_id', 'user_id', 'rate', 'text', 'expected_code'),
    [
        (100, 1, 10, 'good film', 404),
        (3, 2, 5, 'average film', 404),
        ('invalid', 1, 6, 'some review text', 422),
        (1, 1, -5, None, 422),
        (1, 1, 12, None, 422),
        (1, 1, 6, '', 422),
    ],
)
def test_update_movie_review_incorrect_args(
    movie_id, user_id, rate, text, session, unauth_client, db_reviews, expected_code
):
    db_review_before_request = (
        session.query(models.Review)
        .filter_by(movie_id=movie_id, user_id=user_id)
        .one_or_none()
    )
    auth = (f'username{user_id}', f'password{user_id}')
    unauth_client.auth = auth
    response = unauth_client.put(
        f'/movies/{movie_id}/reviews', json={'rate': rate, 'text': text}
    )

    db_review_after_request = (
        session.query(models.Review)
        .filter_by(movie_id=movie_id, user_id=user_id)
        .one_or_none()
    )

    assert response.status_code == expected_code
    assert 'detail' in response.json()
    if db_review_before_request:
        assert db_review_after_request == db_review_before_request


@pytest.mark.parametrize('movie_id', [1, 2, 3])
def test_delete_movie_correct_args(auth_client, session, movie_id, db_movies):
    response = auth_client.delete(f'/movies/{movie_id}')

    db_movies_count = session.query(models.Movie).count()
    db_reviews = session.query(models.Review).filter_by(movie_id=movie_id).all()

    assert response.status_code == 200
    assert response.json() == movie_id
    assert db_movies_count == 2
    assert not db_reviews


@pytest.mark.parametrize('movie_id', [100, 'invalid'])
def test_delete_movie_incorrect_args(auth_client, session, movie_id, db_movies):
    response = auth_client.delete(f'/movies/{movie_id}')

    db_movies_count = session.query(models.Movie).count()
    expected_code = 422 if movie_id == 'invalid' else 404

    assert response.status_code == expected_code
    assert 'detail' in response.json()
    assert db_movies_count == 3
