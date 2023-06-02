import time
from pathlib import Path

import pytest
from django.conf import settings

from django_web_utils import settings_utils


@pytest.fixture(autouse=True)
def clean_override_files():
    yield

    path = Path(settings.OVERRIDE_PATH)
    for p in path.parent.glob(f'{path.name}*'):
        p.unlink()


@pytest.fixture()
def override_file():
    path = Path(settings.OVERRIDE_PATH)
    path.write_text(
        'BOOL = True\n'
        'BOOL_2 = False\n'
        '\n'
        '# Comment\n'
        'DICT = {"nope": 24}\n'
    )

    yield path

    path.unlink(missing_ok=True)


def _get_override_files():
    path = Path(settings.OVERRIDE_PATH)
    return sorted(
        p.name
        for p in path.parent.iterdir()
        if p.name.startswith(path.name)
    )


def test_backup_settings__no_override():
    path = settings_utils.backup_settings()
    assert path is None


def test_backup_settings__with_override(override_file):
    path = settings_utils.backup_settings()
    assert path is not None
    assert path != override_file
    assert path.read_text() == override_file.read_text()
    mtime = path.stat().st_mtime

    # Second attempt the same day should return the same file
    path = settings_utils.backup_settings()
    assert path is not None
    assert path != override_file
    assert path.read_text() == override_file.read_text()
    assert path.stat().st_mtime == mtime


def test_backup_settings__max_reached(override_file):
    for i in range(10, 22):
        Path(f'{override_file}.backup_2023-01-{i:02}.py').touch()

    assert _get_override_files() == [
        'djwutils_override.py',
        'djwutils_override.py.backup_2023-01-10.py',
        'djwutils_override.py.backup_2023-01-11.py',
        'djwutils_override.py.backup_2023-01-12.py',
        'djwutils_override.py.backup_2023-01-13.py',
        'djwutils_override.py.backup_2023-01-14.py',
        'djwutils_override.py.backup_2023-01-15.py',
        'djwutils_override.py.backup_2023-01-16.py',
        'djwutils_override.py.backup_2023-01-17.py',
        'djwutils_override.py.backup_2023-01-18.py',
        'djwutils_override.py.backup_2023-01-19.py',
        'djwutils_override.py.backup_2023-01-20.py',
        'djwutils_override.py.backup_2023-01-21.py',
    ]

    path = settings_utils.backup_settings()
    assert path is not None
    assert path != override_file
    assert path.read_text() == override_file.read_text()

    assert _get_override_files() == [
        'djwutils_override.py',
        'djwutils_override.py.backup_2023-01-13.py',
        'djwutils_override.py.backup_2023-01-14.py',
        'djwutils_override.py.backup_2023-01-15.py',
        'djwutils_override.py.backup_2023-01-16.py',
        'djwutils_override.py.backup_2023-01-17.py',
        'djwutils_override.py.backup_2023-01-18.py',
        'djwutils_override.py.backup_2023-01-19.py',
        'djwutils_override.py.backup_2023-01-20.py',
        'djwutils_override.py.backup_2023-01-21.py',
        path.name,
    ]


def test_set_settings__no_values():
    success, msg = settings_utils.set_settings()
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


def test_set_settings__invalid_key():
    success, msg = settings_utils.set_settings(**{'0a': 1})
    assert not success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


@pytest.mark.parametrize('override_content', [
    pytest.param(None, id='no override'),
    pytest.param(False, id='empty override'),
    pytest.param(True, id='filled override'),
])
def test_set_and_remove_settings(override_file, override_content):
    if override_content is None:
        override_file.unlink()
    elif override_content is False:
        override_file.write_text('')

    success, msg = settings_utils.set_settings(
        STR='test text',
        NONE=None,
        BOOL=False,
        INT=47,
        FLOAT=0.89,
        DICT={'1234': {456: None}},
        LIST=['test', 12],
        TUPLE=('val', 48),
    )
    assert success, msg

    path = Path(settings.OVERRIDE_PATH)
    assert path.exists()
    if override_content is True:
        assert path.read_text() == '''BOOL = False
BOOL_2 = False

# Comment
DICT = {'1234': {456: None, }, }
STR = 'test text'
NONE = None
INT = 47
FLOAT = 0.89
LIST = ['test', 12, ]
TUPLE = ('val', 48, )
'''
    else:
        assert path.read_text() == '''STR = 'test text'
NONE = None
BOOL = False
INT = 47
FLOAT = 0.89
DICT = {'1234': {456: None, }, }
LIST = ['test', 12, ]
TUPLE = ('val', 48, )
'''
    if override_content is None:
        assert len(_get_override_files()) == 1
    else:
        assert len(_get_override_files()) == 2  # A backup should have been made

    success, msg = settings_utils.remove_settings('BOOL', 'LIST')
    assert success, msg
    if override_content is True:
        assert path.read_text() == '''BOOL_2 = False

# Comment
DICT = {'1234': {456: None, }, }
STR = 'test text'
NONE = None
INT = 47
FLOAT = 0.89
TUPLE = ('val', 48, )
'''
    else:
        assert path.read_text() == '''STR = 'test text'
NONE = None
INT = 47
FLOAT = 0.89
DICT = {'1234': {456: None, }, }
TUPLE = ('val', 48, )
'''


def test_remove_settings__no_names():
    success, msg = settings_utils.remove_settings()
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


def test_remove_settings__no_override():
    success, msg = settings_utils.remove_settings('TEST')
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


def test_remove_settings__invalid_key():
    success, msg = settings_utils.remove_settings(*['0a'])
    assert not success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


def test_reload_settings():
    old_value = settings.TIME_NOW
    time.sleep(0.0001)
    # The reload_settings function doesn't return a new instance
    assert settings_utils.reload_settings() is None
    # Global settings have been updated
    assert old_value != settings.TIME_NOW
