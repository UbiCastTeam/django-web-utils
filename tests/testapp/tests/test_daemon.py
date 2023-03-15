import logging
import os
import socket
import time
from datetime import timedelta

import pytest
from django_web_utils.daemon.base import BaseDaemon
from django_web_utils.daemon import lock

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
            with pytest.raises(lock.LockAlreadyAcquired):
                dummy_fct()
    else:
        assert dummy_fct() == 'dummy'
