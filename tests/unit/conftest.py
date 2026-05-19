from pathlib import Path
import shutil

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
import pytest

PASSWORD_CACHE = {}


@pytest.fixture(autouse=True)
def clear_mailbox():
    mail.outbox = []


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture()
def tmp_dir():
    path = Path('/tmp/djwutils')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()

    yield path

    if path.exists():
        shutil.rmtree(path)


@pytest.fixture()
def password_generator():
    """
    This function is used to do hashing operations only once per password
    """
    def get_password_hash(password):
        if password in PASSWORD_CACHE:
            return PASSWORD_CACHE[password]
        if not password:
            value = ''
        else:
            user = User()
            user.set_password(password)
            value = user.password
        PASSWORD_CACHE[password] = value
        return value

    return get_password_hash
