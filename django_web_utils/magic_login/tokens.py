from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator


def generate_token(user: AbstractBaseUser, session_key: str) -> str:
    """
    Generate a token for a user.
    """
    generator = PasswordResetTokenGenerator()
    generator.key_salt = session_key
    return generator.make_token(user)


def check_token(user: AbstractBaseUser, session_key: str, token: str) -> bool:
    """
    Check the validity of a token for a user.
    """
    generator = PasswordResetTokenGenerator()
    generator.key_salt = session_key
    return generator.check_token(user, token)
