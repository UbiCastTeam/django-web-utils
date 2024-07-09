import os
from pathlib import Path

import pytest
from django.utils.translation import activate

from django_web_utils import files_utils

pytestmark = pytest.mark.django_db

storage_dir = Path(__file__).resolve().parent.parent.parent / 'storage'


@pytest.fixture()
def fr_language():
    activate('fr')
    yield
    activate('en')


@pytest.mark.parametrize('size, expected', [
    pytest.param(123, '123 B', id='B'),
    pytest.param(123456, '123.5 kB', id='k'),
    pytest.param(123456 * 1000, '123.5 MB', id='M'),
    pytest.param(123456 * 1000 ** 2, '123.5 GB', id='G'),
    pytest.param(123456 * 1000 ** 3, '123.5 TB', id='T'),
    pytest.param(123456 * 1000 ** 4, '123.5 PB', id='P'),
    pytest.param(123456 * 1000 ** 5, '123.5 EB', id='E'),
    pytest.param(123456 * 1000 ** 6, '123.5 ZB', id='Z'),
    pytest.param(123456 * 1000 ** 7, '123.5 YB', id='Y'),
    pytest.param(123456 * 1000 ** 8, '123456.0 YB', id='max'),
])
def test_get_size_display(size, expected):
    assert files_utils.get_size_display(size) == expected


@pytest.mark.usefixtures('fr_language')
def test_get_size_display__translation():
    assert files_utils.get_size_display(123456789) == '123.5 Mo'


def test_get_size_display__file():
    path = storage_dir / 'a dir/test file.txt'
    assert files_utils.get_size_display(path=path) == '3 B'
    assert files_utils.get_size_display(path=str(path)) == '3 B'


def test_get_size_display__dir():
    assert files_utils.get_size_display(path=storage_dir) == '10.4 kB'
    assert files_utils.get_size_display(path=str(storage_dir)) == '10.4 kB'


def test_get_new_path():
    assert files_utils.get_new_path(Path('test.mp4')).name == 'test_1.mp4'
    assert files_utils.get_new_path('test.mp4').name == 'test_1.mp4'


def test_get_new_path__extension():
    assert files_utils.get_new_path(Path('test.mp4'), new_extension='mkv').name == 'test_1.mkv'
    assert files_utils.get_new_path('test.mp4', new_extension='mkv').name == 'test_1.mkv'


def test_reverse_read():
    path = storage_dir / 'a dir/lorem.md'
    reader = files_utils.reverse_read(path, buf_size=40)
    assert next(reader) == b' lorem varius purus. Curabitur eu amet.\n'
    assert next(reader) == b'agna fermentum augue, et ultricies lacus'


def test_backup_file(tmp_dir):
    path = tmp_dir / 'test.file'
    path.touch()
    os.utime(path, (1602179630, 1602179630))

    # Make a backup
    assert files_utils.backup_file(path).name == 'test.file.backup_2020-10-08.file'
    assert sorted(p.name for p in tmp_dir.iterdir()) == [
        'test.file', 'test.file.backup_2020-10-08.file'
    ]

    # Second call with same mtime, backup is already done
    assert files_utils.backup_file(path).name == 'test.file.backup_2020-10-08.file'
    assert sorted(p.name for p in tmp_dir.iterdir()) == [
        'test.file', 'test.file.backup_2020-10-08.file'
    ]

    # Change mtime and make another backup
    os.utime(path, (1602279630, 1602279630))
    assert files_utils.backup_file(path).name == 'test.file.backup_2020-10-09.file'
    assert sorted(p.name for p in tmp_dir.iterdir()) == [
        'test.file', 'test.file.backup_2020-10-08.file', 'test.file.backup_2020-10-09.file'
    ]

    # Trigger max files
    os.utime(path, (1602379630, 1602379630))
    assert files_utils.backup_file(path, max_backups=2).name == 'test.file.backup_2020-10-11.file'
    assert sorted(p.name for p in tmp_dir.iterdir()) == [
        'test.file', 'test.file.backup_2020-10-09.file', 'test.file.backup_2020-10-11.file'
    ]


def test_backup_file__inexistent():
    assert files_utils.backup_file(Path('/nope')) is None
