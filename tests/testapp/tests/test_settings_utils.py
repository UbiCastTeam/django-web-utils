import time
from pathlib import Path

import pytest

from django_web_utils import settings_utils


@pytest.fixture(autouse=True)
def clean_override_files(settings):
    yield

    path = settings.OVERRIDE_PATH
    for p in path.parent.glob(f'{path.stem}*'):
        p.unlink()


@pytest.fixture()
def override_file_toml(settings):
    settings.OVERRIDE_PATH = settings.OVERRIDE_PATH.parent / f'{settings.OVERRIDE_PATH.stem}.toml'

    path = settings.OVERRIDE_PATH
    path.write_text(
        'BOOL = true\n'
        'BOOL_2 = false\n'
        '\n'
        '# Comment\n'
        'DICT = {"nope": 24}\n'
    )

    yield path

    path.unlink(missing_ok=True)


@pytest.fixture()
def override_file_python(settings):
    settings.OVERRIDE_PATH = settings.OVERRIDE_PATH.parent / f'{settings.OVERRIDE_PATH.stem}.py'

    path = settings.OVERRIDE_PATH
    path.write_text(
        'BOOL = True\n'
        'BOOL_2 = False\n'
        '\n'
        '# Comment\n'
        'DICT = {"nope": 24}\n'
    )

    yield path

    path.unlink(missing_ok=True)


def _get_override_files(override_path):
    return sorted(
        p.name
        for p in override_path.parent.glob(f'{override_path.stem}*')
    )


def test_backup_settings__no_override():
    path = settings_utils.backup_settings()
    assert path is None


@pytest.mark.parametrize('override_fxt', ['override_file_toml', 'override_file_python'])
def test_backup_settings__with_override(request, override_fxt):
    override_file = request.getfixturevalue(override_fxt)

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


@pytest.mark.parametrize('override_fxt', ['override_file_toml', 'override_file_python'])
def test_backup_settings__max_reached(request, override_fxt):
    override_file = request.getfixturevalue(override_fxt)
    ext = override_file.suffix

    for i in range(10, 22):
        Path(f'{override_file}.backup_2023-01-{i:02}{ext}').touch()

    assert _get_override_files(override_file) == [
        f'djwutils_override{ext}',
        f'djwutils_override{ext}.backup_2023-01-10{ext}',
        f'djwutils_override{ext}.backup_2023-01-11{ext}',
        f'djwutils_override{ext}.backup_2023-01-12{ext}',
        f'djwutils_override{ext}.backup_2023-01-13{ext}',
        f'djwutils_override{ext}.backup_2023-01-14{ext}',
        f'djwutils_override{ext}.backup_2023-01-15{ext}',
        f'djwutils_override{ext}.backup_2023-01-16{ext}',
        f'djwutils_override{ext}.backup_2023-01-17{ext}',
        f'djwutils_override{ext}.backup_2023-01-18{ext}',
        f'djwutils_override{ext}.backup_2023-01-19{ext}',
        f'djwutils_override{ext}.backup_2023-01-20{ext}',
        f'djwutils_override{ext}.backup_2023-01-21{ext}',
    ]

    path = settings_utils.backup_settings()
    assert path is not None
    assert path != override_file
    assert path.read_text() == override_file.read_text()

    assert _get_override_files(override_file) == [
        f'djwutils_override{ext}',
        f'djwutils_override{ext}.backup_2023-01-13{ext}',
        f'djwutils_override{ext}.backup_2023-01-14{ext}',
        f'djwutils_override{ext}.backup_2023-01-15{ext}',
        f'djwutils_override{ext}.backup_2023-01-16{ext}',
        f'djwutils_override{ext}.backup_2023-01-17{ext}',
        f'djwutils_override{ext}.backup_2023-01-18{ext}',
        f'djwutils_override{ext}.backup_2023-01-19{ext}',
        f'djwutils_override{ext}.backup_2023-01-20{ext}',
        f'djwutils_override{ext}.backup_2023-01-21{ext}',
        path.name,
    ]


def test_set_settings__no_values(settings):
    success, msg = settings_utils.set_settings()
    assert success, msg
    path = settings.OVERRIDE_PATH
    assert not path.exists()


def test_set_settings__invalid_key(settings):
    success, msg = settings_utils.set_settings(**{'0a': 1})
    assert not success, msg
    path = settings.OVERRIDE_PATH
    assert not path.exists()


def test_set_settings__none__toml(settings):
    settings.OVERRIDE_PATH = settings.OVERRIDE_PATH.parent / f'{settings.OVERRIDE_PATH.stem}.toml'

    with pytest.raises(ValueError) as err:
        settings_utils.set_settings(NONE=None)
    assert 'The toml format does not support None.' in str(err.value)


def test_set_settings__none__python(settings):
    settings.OVERRIDE_PATH = settings.OVERRIDE_PATH.parent / f'{settings.OVERRIDE_PATH.stem}.py'

    success, msg = settings_utils.set_settings(NONE=None)
    assert success, msg
    path = settings.OVERRIDE_PATH
    assert path.read_text() == 'NONE = None\n'


@pytest.mark.parametrize('ext', ['toml', 'py'])
def test_set_settings__multiline(settings, ext):
    settings.OVERRIDE_PATH = settings.OVERRIDE_PATH.parent / f'{settings.OVERRIDE_PATH.stem}.{ext}'

    # Add a multiline setting
    success, msg = settings_utils.set_settings(MULTILINE='1\n\r"\'2\\')
    assert success, msg
    path = settings.OVERRIDE_PATH
    if ext == 'toml':
        assert path.read_text() == '''MULTILINE = "1\\n\\"'2\\\\"\n'''
    else:
        assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\n'''

    # Add another setting
    success, msg = settings_utils.set_settings(TEST=True)
    assert success, msg
    path = settings.OVERRIDE_PATH
    if ext == 'toml':
        assert path.read_text() == '''MULTILINE = "1\\n\\"'2\\\\"\nTEST = true\n'''
    else:
        assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\n'''

    # Send same value for the multiline setting
    # (was causing issue https://redmine.ubicast.net/issues/38214)
    success, msg = settings_utils.set_settings(MULTILINE='1\n\r"\'2\\')
    assert success, msg
    path = settings.OVERRIDE_PATH
    if ext == 'toml':
        assert path.read_text() == '''MULTILINE = "1\\n\\"'2\\\\"\nTEST = true\n'''
    else:
        assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\n'''

    # Add another multiline setting
    success, msg = settings_utils.set_settings(MULTI2='test \'45é\n')
    assert success, msg
    path = settings.OVERRIDE_PATH
    if ext == 'toml':
        assert path.read_text() == '''MULTILINE = "1\\n\\"'2\\\\"\nTEST = true\nMULTI2 = "test '45é\\n"\n'''
    else:
        assert path.read_text() == '''MULTILINE = '1\\n"\\'2\\\\'\nTEST = True\nMULTI2 = "test '45é\\n"\n'''


@pytest.mark.parametrize('override_fxt', ['override_file_toml', 'override_file_python'])
@pytest.mark.parametrize('override_content', [
    pytest.param(None, id='no override'),
    pytest.param(False, id='empty override'),
    pytest.param(True, id='filled override'),
])
def test_set_and_remove_settings(request, settings, override_fxt, override_content):
    override_file = request.getfixturevalue(override_fxt)

    if override_content is None:
        override_file.unlink()
    elif override_content is False:
        override_file.write_text('')

    success, msg = settings_utils.set_settings(
        STR='test text',
        BOOL=False,
        INT=47,
        FLOAT=0.89,
        DICT={'1234': {456: True}},
        LIST=['test', 12],
        TUPLE=('val', 48),
        MULTILINE='1\n2 \' "eé',
    )
    assert success, msg

    path = settings.OVERRIDE_PATH
    assert path.exists()
    if override_content is True:
        if override_file.suffix == '.toml':
            assert path.read_text() == '''BOOL = false
BOOL_2 = false

# Comment
DICT = {"1234": {456: true}}
STR = "test text"
INT = 47
FLOAT = 0.89
LIST = ["test", 12]
TUPLE = ["val", 48]
MULTILINE = "1\\n2 ' \\"eé"
'''
        else:
            assert path.read_text() == '''BOOL = False
BOOL_2 = False

# Comment
DICT = {'1234': {456: True}}
STR = 'test text'
INT = 47
FLOAT = 0.89
LIST = ['test', 12]
TUPLE = ('val', 48)
MULTILINE = '1\\n2 \\' "eé'
'''
    else:
        if override_file.suffix == '.toml':
            assert path.read_text() == '''STR = "test text"
BOOL = false
INT = 47
FLOAT = 0.89
DICT = {"1234": {456: true}}
LIST = ["test", 12]
TUPLE = ["val", 48]
MULTILINE = "1\\n2 ' \\"eé"
'''
        else:
            assert path.read_text() == '''STR = 'test text'
BOOL = False
INT = 47
FLOAT = 0.89
DICT = {'1234': {456: True}}
LIST = ['test', 12]
TUPLE = ('val', 48)
MULTILINE = '1\\n2 \\' "eé'
'''
    if override_content is None:
        assert len(_get_override_files(override_file)) == 1
    else:
        assert len(_get_override_files(override_file)) == 2  # A backup should have been made

    success, msg = settings_utils.remove_settings('BOOL', 'LIST')
    assert success, msg
    if override_content is True:
        if override_file.suffix == '.toml':
            assert path.read_text() == '''BOOL_2 = false

# Comment
DICT = {"1234": {456: true}}
STR = "test text"
INT = 47
FLOAT = 0.89
TUPLE = ["val", 48]
MULTILINE = "1\\n2 ' \\"eé"
'''
        else:
            assert path.read_text() == '''BOOL_2 = False

# Comment
DICT = {'1234': {456: True}}
STR = 'test text'
INT = 47
FLOAT = 0.89
TUPLE = ('val', 48)
MULTILINE = '1\\n2 \\' "eé'
'''
    else:
        if override_file.suffix == '.toml':
            assert path.read_text() == '''STR = "test text"
INT = 47
FLOAT = 0.89
DICT = {"1234": {456: true}}
TUPLE = ["val", 48]
MULTILINE = "1\\n2 ' \\"eé"
'''
        else:
            assert path.read_text() == '''STR = 'test text'
INT = 47
FLOAT = 0.89
DICT = {'1234': {456: True}}
TUPLE = ('val', 48)
MULTILINE = '1\\n2 \\' "eé'
'''


def test_remove_settings__no_names(settings):
    success, msg = settings_utils.remove_settings()
    assert success, msg
    path = settings.OVERRIDE_PATH
    assert not path.exists()


def test_remove_settings__no_override(settings):
    success, msg = settings_utils.remove_settings('TEST')
    assert success, msg
    path = settings.OVERRIDE_PATH
    assert not path.exists()


def test_remove_settings__invalid_key(settings):
    success, msg = settings_utils.remove_settings(*['0a'])
    assert not success, msg
    path = settings.OVERRIDE_PATH
    assert not path.exists()


def test_reload_settings(settings):
    old_value = settings.TIME_NOW
    time.sleep(0.0001)
    # The reload_settings function doesn't return a new instance
    assert settings_utils.reload_settings() is None
    # Global settings have been updated
    assert old_value != settings.TIME_NOW
