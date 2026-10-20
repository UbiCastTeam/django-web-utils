import os
from pathlib import Path
import time

from django.conf import settings
import pytest

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


def test_set_settings__multiline():
    # Add a multiline setting
    success, msg = settings_utils.set_settings(MULTILINE='1\n\r"\'2\\')
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\n'''

    # Add another setting
    success, msg = settings_utils.set_settings(TEST=True)
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\n'''

    # Send same value for the multiline setting
    # (was causing issue https://redmine.ubicast.net/issues/38214)
    success, msg = settings_utils.set_settings(MULTILINE='1\n\r"\'2\\')
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\n'''

    # Add another multiline setting
    success, msg = settings_utils.set_settings(MULTI2="test '45\n")
    assert success, msg
    path = Path(settings.OVERRIDE_PATH)
    assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\nMULTI2 = "test '45\\n"\n'''


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
        MULTILINE='1\n2 \' "e',
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
MULTILINE = '1\\n2 \\' "e'
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
MULTILINE = '1\\n2 \\' "e'
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
MULTILINE = '1\\n2 \\' "e'
'''
    else:
        assert path.read_text() == '''STR = 'test text'
NONE = None
INT = 47
FLOAT = 0.89
DICT = {'1234': {456: None, }, }
TUPLE = ('val', 48, )
MULTILINE = '1\\n2 \\' "e'
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


def test_set_settings__invalid_key_suffix():
    # The whole key must be validated, not only its beginning
    success, msg = settings_utils.set_settings(VALID=1, **{'INVALID\nimport os': 1})
    assert not success, msg
    assert not hasattr(settings, 'VALID')
    path = Path(settings.OVERRIDE_PATH)
    assert not path.exists()


def test_remove_settings__invalid_key_suffix():
    success, msg = settings_utils.remove_settings('INVALID = 1\nimport os')
    assert not success, msg


def test_set_settings__keep_file_mode():
    path = Path(settings.OVERRIDE_PATH)
    path.write_text('A = 1\n')
    path.chmod(0o600)
    success, msg = settings_utils.set_settings(B=2)
    assert success, msg
    assert path.read_text() == 'A = 1\nB = 2\n'
    assert path.stat().st_mode & 0o777 == 0o600
    # No temporary file must remain
    assert not [p for p in path.parent.iterdir() if p.name.endswith('.tmp')]


def test_write_file_atomically__symlink(tmp_dir):
    target = tmp_dir / 'settings_target.py'
    target.write_text('A = 1\n')
    link = tmp_dir / 'settings_link.py'
    link.symlink_to(target)
    settings_utils._write_file_atomically(link, 'A = 2\n')
    # The link is kept and its target is updated
    assert link.is_symlink()
    assert target.read_text() == 'A = 2\n'


def test_write_file_atomically__directory_not_writable(tmp_dir):
    directory = tmp_dir / 'read_only_dir'
    directory.mkdir()
    path = directory / 'settings_override.py'
    path.write_text('A = 1\n')
    directory.chmod(0o555)
    try:
        settings_utils._write_file_atomically(path, 'A = 2\n')
    finally:
        directory.chmod(0o755)
    assert path.read_text() == 'A = 2\n'
    assert [p.name for p in directory.iterdir()] == ['settings_override.py']


def test_write_file_atomically__owner_not_kept(tmp_dir, monkeypatch):
    path = tmp_dir / 'settings_override.py'
    path.write_text('A = 1\n')
    initial_inode = path.stat().st_ino

    # Simulate a file owned by another user
    real_stat = Path.stat

    def fake_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if self == path:
            return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink, st.st_uid + 1) + tuple(st)[5:])
        return st

    monkeypatch.setattr(Path, 'stat', fake_stat)

    def fake_chown(*args):
        raise PermissionError('Operation not permitted')

    monkeypatch.setattr(os, 'chown', fake_chown)
    settings_utils._write_file_atomically(path, 'A = 2\n')
    assert path.read_text() == 'A = 2\n'
    # The file has been written directly (not replaced)
    assert real_stat(path).st_ino == initial_inode
    assert [p.name for p in tmp_dir.iterdir()] == ['settings_override.py']
