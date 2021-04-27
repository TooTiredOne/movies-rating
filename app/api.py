from threading import Thread
from typing import Any

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from flask import Flask, redirect
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

import app.routing.movies as movies_routing
import app.routing.users as users_routing
from app import models
from app.database import Session, engine
from app.dependencies import UnauthorizedException

models.DeclarativeBase.metadata.create_all(bind=engine)
app = FastAPI()


@app.exception_handler(UnauthorizedException)
def unauthorized_exception_handler() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={'detail': 'Incorrect username or password'},
        headers={'WWW-Authenticate': 'Basic'},
    )


app.include_router(
    users_routing.router,
    prefix='/users',
    tags=['users'],
)

app.include_router(
    movies_routing.router,
    prefix='/movies',
    tags=['movies'],
)


class UserView(ModelView):
    column_auto_select_related = True
    column_list = ('id', 'username', 'reviews')


class MovieView(ModelView):
    column_auto_select_related = True
    column_list = ('id', 'title', 'release_year', 'avg_rating', 'reviews')

    form_widget_args = {'avg_rating': {'disabled': True}}


class ReviewBaseView(ModelView):
    column_list = (
        'id',
        'user.username',
        'user.id',
        'movie.title',
        'movie.id',
        'movie.release_year',
        'rate',
        'text',
        'datetime',
    )

    column_sortable_list = (
        'id',
        'user.username',
        'user.id',
        'movie.id',
        'movie.title',
        'movie.release_year',
    )

    # column_searchable_list = (models.User.id, models.User.username, models.Movie.title)

    column_labels = {
        'user.username': 'Username',
        'user.id': 'User Id',
        'movie.title': 'Movie Title',
        'movie.id': 'Movie Id',
        'movie.release_year': 'Movie Year',
    }


class ReviewUserView(ReviewBaseView):
    column_searchable_list = (models.User.id, models.User.username)


class ReviewMovieView(ReviewBaseView):
    column_searchable_list = (models.Movie.id, models.Movie.title)


flask_app = Flask(__name__)
flask_app.secret_key = 'pls work'


@flask_app.route('/')
def redirect_to_admin() -> Any:
    return redirect('/admin')


def _start_flask_admin_page() -> None:
    admin = Admin(flask_app, name='movies blog', template_mode='bootstrap3')
    session = Session()
    admin.add_view(MovieView(models.Movie, session, name='Movie'))
    admin.add_view(UserView(models.User, session, name='User'))
    admin.add_view(
        ReviewUserView(
            models.Review, session, name='Reviews-Users', endpoint='reviews-users'
        )
    )
    admin.add_view(
        ReviewMovieView(
            models.Review, session, name='Reviews-Movies', endpoint='reviews-movies'
        )
    )
    flask_app.run(port=5000)


if __name__ == '__main__':
    thread = Thread(target=_start_flask_admin_page)
    thread.daemon = True
    thread.start()
    uvicorn.run(app, port=8000)
