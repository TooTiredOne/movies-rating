import secrets
from typing import Generator

from fastapi import Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app import schemas
from app.crud_users import get_user_by_username
from app.database import Session
from app.utils import make_password_hash

# pylint: disable=broad-except


security = HTTPBasic()


def get_session() -> Generator[Session, None, None]:
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()


class UnauthorizedException(Exception):
    pass


# implements basic auth
def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> schemas.User:
    db_user = get_user_by_username(username=credentials.username, session=session)

    if not db_user:
        raise UnauthorizedException

    correct_password = secrets.compare_digest(
        make_password_hash(credentials.password), db_user.hashed_password
    )

    if not correct_password:
        raise UnauthorizedException

    return schemas.User.from_orm(db_user)
