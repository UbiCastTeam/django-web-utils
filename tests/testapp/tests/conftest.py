from pathlib import Path
import shutil

from django.core import mail
from django.core.cache import cache
import pytest


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
