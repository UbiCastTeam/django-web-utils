"""
Lock functions
This simple lock system is based on a file and is using the system hostname as reference.
"""
import datetime
import logging
import socket
import time
from pathlib import Path
from functools import wraps

logger = logging.getLogger('djwutils.daemon.lock')


class LockAlreadyAcquired(Exception):
    pass


def acquire_lock(path, timeout=None):
    # The timeout value can be None or a timedelta object
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hostname = socket.gethostname()
    try:
        mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    except FileNotFoundError:
        pass
    else:
        if timeout and mtime < datetime.datetime.now() - timeout:
            logger.info('Lock file "%s" has timed out.', path)
        else:
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
            else:
                logger.info(
                    'Lock file "%s" already exists and is attributed to current hostname.',
                    path
                )
    path.write_text(hostname)
    logger.info('Lock file "%s" acquired.', path)
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
                    raise LockAlreadyAcquired(msg)
            else:
                try:
                    return function(*args, **kwargs)
                finally:
                    release_lock(path)
        return _wrapped_function
    return _wrap
