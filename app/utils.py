import bcrypt


def make_password_hash(password: str) -> str:
    salt = b'$2b$12$yJR/5VAr5eKdxOdnbQLWiu'
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
