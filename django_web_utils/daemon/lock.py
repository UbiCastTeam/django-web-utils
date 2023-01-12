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
            logger.info(f'Lock file "{path}" has timed out.')
        else:
            try:
                content = path.read_text()
            except OSError as e:
                logger.debug(f'Failed to read lock file "{path}", retrying in 2s. Error was: {e}')
                time.sleep(2)
                try:
                    content = path.read_text()
                except OSError as e:
                    logger.info(f'Failed to read lock file "{path}", assuming another host is using it. Error was: {e}')
                    return False
            if content != hostname:
                logger.info(f'Could not acquire lock file "{path}" because it is currently attributed to host "{content}".')
                return False
            else:
                logger.info(f'Lock file "{path}" already exists and is attributed to current hostname.')
    path.write_text(hostname)
    logger.info(f'Lock file "{path}" acquired.')
    return True


def release_lock(path):
    path = Path(path)
    if path.exists():
        hostname = socket.gethostname()
        content = path.read_text()
        if content == hostname:
            path.unlink(missing_ok=True)
            logger.info(f'Lock file "{path}" released.')
        else:
            logger.warning(f'Cannot release lock file "{path}" because it is owned by host "{content}".')
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
