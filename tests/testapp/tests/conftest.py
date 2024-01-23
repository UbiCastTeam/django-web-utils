import shutil
from pathlib import Path

import pytest
from django.core import mail


@pytest.fixture(autouse=True)
def clear_mailbox():
    mail.outbox = []


@pytest.fixture()
def tmp_dir():
    path = Path('/tmp/djwutils')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()

    yield path

    if path.exists():
        shutil.rmtree(path)
