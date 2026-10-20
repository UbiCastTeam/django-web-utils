"""
Lock functions
This simple lock system is based on a file and is using the system hostname as reference.
"""
from functools import wraps
import logging
import os
from pathlib import Path
import socket
import time
import uuid

logger = logging.getLogger('djwutils.daemon.lock')


class LockAlreadyAcquiredError(Exception):
    pass


def _create_lock_file(path, hostname):
    """
    Create the lock file atomically.
    Returns False if the file already exists.
    """
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, 'w') as fo:
        fo.write(hostname)
    return True


def _remove_stale_lock(path, stale_stat):
    """
    Remove the timed out lock file described by `stale_stat`.
    The file is renamed before being removed so that it is possible to check that it was not
    replaced in the meantime by a fresh lock file from another process (which must not be removed).
    Returns False if the lock file has been replaced by another process.
    """
    stale_path = path.with_name(f'{path.name}.{uuid.uuid4().hex}.stale')
    try:
        os.rename(path, stale_path)
    except FileNotFoundError:
        # The lock file has already been removed by another process
        return True
    try:
        st = stale_path.stat()
        if (st.st_dev, st.st_ino, st.st_mtime_ns) == (
            stale_stat.st_dev, stale_stat.st_ino, stale_stat.st_mtime_ns
        ):
            return True
        # The renamed file is a fresh lock file from another process, restore it (without overwriting)
        try:
            os.link(stale_path, path)
        except FileExistsError:
            logger.warning('Failed to restore lock file "%s" because it has been recreated.', path)
        return False
    finally:
        stale_path.unlink(missing_ok=True)


def acquire_lock(path, timeout=None):
    # The timeout value can be None or a timedelta object
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hostname = socket.gethostname()
    if _create_lock_file(path, hostname):
        logger.info('Lock file "%s" acquired.', path)
        return True

    # The lock file already exists
    try:
        lock_stat = path.stat()
    except FileNotFoundError:
        # The lock has been released in the meantime
        lock_stat = None
    if lock_stat is None or (timeout and lock_stat.st_mtime < time.time() - timeout.total_seconds()):
        if lock_stat is not None:
            logger.info('Lock file "%s" has timed out.', path)
            if not _remove_stale_lock(path, lock_stat):
                logger.info('Could not acquire lock file "%s" because it has been acquired by another process.', path)
                return False
        if _create_lock_file(path, hostname):
            logger.info('Lock file "%s" acquired.', path)
            return True
        logger.info('Could not acquire lock file "%s" because it has been acquired by another process.', path)
        return False

    try:
        content = path.read_text()
    except OSError as err:
        logger.debug(
            'Failed to read lock file "%s", retrying in 2s. Error was: %s',
            path, err
        )
        time.sleep(2)
        try:
            content = path.read_text()
        except OSError as err:
            logger.info(
                'Failed to read lock file "%s", assuming another host is using it. Error was: %s',
                path, err
            )
            return False
    if content != hostname:
        logger.info(
            'Could not acquire lock file "%s" because it is currently attributed to host "%s".',
            path, content
        )
        return False
    logger.info('Lock file "%s" already exists and is attributed to current hostname.', path)
    # Refresh the modification date of the lock
    path.write_text(hostname)
    return True


def release_lock(path):
    path = Path(path)
    if path.exists():
        hostname = socket.gethostname()
        content = path.read_text()
        if content == hostname:
            path.unlink(missing_ok=True)
            logger.info('Lock file "%s" released.', path)
        else:
            logger.warning('Cannot release lock file "%s" because it is owned by host "%s".', path, content)
            return False
    return True


def require_lock(path, timeout=None, silent=True):
    def _wrap(function):
        @wraps(function)
        def _wrapped_function(*args, **kwargs):
            if not acquire_lock(path, timeout):
                msg = f'Could not get lock "{path}".'
                if silent:
                    logger.info(msg)
                else:
                    raise LockAlreadyAcquiredError(msg)
            else:
                try:
                    return function(*args, **kwargs)
                finally:
                    release_lock(path)
        return _wrapped_function
    return _wrap
