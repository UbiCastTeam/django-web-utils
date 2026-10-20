from datetime import timedelta
import logging
import os
import socket
import time

import pytest

from django_web_utils.daemon import lock
from django_web_utils.daemon.base import BaseDaemon

logger = logging.getLogger(__name__)


@pytest.fixture()
def lock_path(tmp_dir):
    path = tmp_dir / 'lock-file'
    path.unlink(missing_ok=True)

    yield path

    path.unlink(missing_ok=True)


def test_daemons_attrs():
    assert BaseDaemon.get_name() == 'base'


def test_daemon_start():
    logger.info('////!\\\\\\\\ A traceback will be displayed after this line, this is intended, ignore it.')

    class TestDaemon(BaseDaemon):

        def exit(self, code=0):
            # Override exit function to check expected code
            if code != 140:
                raise Exception(f'Unexpected error code (expected 140, got {code}).')
            raise RuntimeError(f'Canceled exit with expected code ({code}).')

    # Logging will be displayed twice because of logging init in the daemon class
    daemon = TestDaemon(['-f', 'start'])
    with pytest.raises(RuntimeError):
        daemon.start()


def test_lock_file__acquire(lock_path):
    acquired = lock.acquire_lock(lock_path)
    assert acquired is True
    assert lock_path.exists()
    assert lock_path.read_text() == socket.gethostname()

    # Acquire same lock (accepted for same system)
    acquired = lock.acquire_lock(lock_path)
    assert acquired is True
    assert lock_path.exists()
    assert lock_path.read_text() == socket.gethostname()


@pytest.mark.parametrize('lock_content, expected_released', [
    pytest.param('', True, id='No current lock'),
    pytest.param('nope', False, id='Lock attributed to other system'),
    pytest.param(socket.gethostname(), True, id='Lock attributed to current system'),
])
def test_lock_file__release(lock_path, lock_content, expected_released):
    if lock_content:
        lock_path.write_text(lock_content)

    released = lock.release_lock(lock_path)
    assert released is expected_released
    assert lock_path.exists() is not expected_released


@pytest.mark.parametrize('timeout, expected_acquired', [
    pytest.param(None, False, id='No timeout'),
    pytest.param(timedelta(seconds=50), True, id='50s timeout'),
    pytest.param(timedelta(seconds=70), False, id='70s timeout'),
])
def test_lock_file__timeout(lock_path, timeout, expected_acquired):
    # Create the lock file with a past mtime
    lock_path.write_text('nope')
    mtime = time.time() - 60
    os.utime(lock_path, (mtime, mtime))

    acquired = lock.acquire_lock(lock_path, timeout=timeout)
    assert acquired is expected_acquired
    assert lock_path.read_text() == (socket.gethostname() if expected_acquired else 'nope')


@pytest.mark.parametrize('silent', [
    pytest.param(True, id='Silent'),
    pytest.param(False, id='Raise'),
])
@pytest.mark.parametrize('lock_content', [
    pytest.param('', id='No current lock'),
    pytest.param('nope', id='Lock attributed to other system'),
    pytest.param(socket.gethostname(), id='Lock attributed to current system'),
])
def test_lock_decorator(lock_path, lock_content, silent):
    if lock_content:
        lock_path.write_text(lock_content)

    @lock.require_lock(lock_path, silent=silent)
    def dummy_fct():
        return 'dummy'

    if lock_content and lock_content != socket.gethostname():
        if silent:
            assert dummy_fct() is None
        else:
            with pytest.raises(lock.LockAlreadyAcquiredError):
                dummy_fct()
    else:
        assert dummy_fct() == 'dummy'


def test_lock_file__acquired_by_other_host(lock_path):
    lock_path.write_text('other-host')
    assert lock.acquire_lock(lock_path) is False
    assert lock_path.read_text() == 'other-host'


def test_check_dir__secure(tmp_dir):
    path = tmp_dir / 'daemon-dir'
    BaseDaemon._check_dir(path)
    assert path.is_dir()
    assert path.stat().st_mode & 0o022 == 0


@pytest.mark.parametrize('kind', ['writable', 'symlink'])
def test_check_dir__insecure(tmp_dir, kind):
    path = tmp_dir / 'daemon-dir'
    if kind == 'writable':
        path.mkdir()
        path.chmod(0o777)
    else:
        target = tmp_dir / 'target'
        target.mkdir()
        path.symlink_to(target, target_is_directory=True)
    with pytest.raises(RuntimeError, match='is insecure'):
        BaseDaemon._check_dir(path)


def test_lock_file__stale_lock_removed(lock_path):
    lock_path.write_text('nope')
    assert lock._remove_stale_lock(lock_path, lock_path.stat()) is True
    assert not lock_path.exists()
    assert [p.name for p in lock_path.parent.iterdir() if p.name.startswith('lock-file')] == []


def test_lock_file__stale_lock_replaced(lock_path):
    lock_path.write_text('nope')
    stale_stat = lock_path.stat()
    # Another process replaces the stale lock with a fresh one before the removal
    lock_path.unlink()
    lock_path.write_text('other-process')
    os.utime(lock_path, ns=(stale_stat.st_atime_ns, stale_stat.st_mtime_ns + 1_000_000_000))

    # The fresh lock must not be removed
    assert lock._remove_stale_lock(lock_path, stale_stat) is False
    assert lock_path.read_text() == 'other-process'
    assert [p.name for p in lock_path.parent.iterdir() if p.name.startswith('lock-file')] == ['lock-file']


def test_log_error__insecure_log_dir(tmp_dir, capsys):
    target = tmp_dir / 'target'
    target.mkdir()
    log_dir = tmp_dir / 'daemon-logs'
    log_dir.symlink_to(target, target_is_directory=True)

    class TestDaemon(BaseDaemon):
        LOG_DIR = log_dir

    daemon = object.__new__(TestDaemon)
    daemon._logging_available = False
    daemon._log_in_file = True
    daemon._log_error(ValueError('test error'))

    # Nothing must be written in the directory targeted by the symbolic link
    assert list(target.iterdir()) == []
    err = capsys.readouterr().err
    assert 'test error' in err
    assert 'is insecure' in err
