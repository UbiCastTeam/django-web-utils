#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Lock function
'''
from functools import wraps
import datetime
import logging
import os
import socket

logger = logging.getLogger('djwutils.daemon.lock')


def acquire_lock(path, timeout=None):
    # timeout can be None or a timedelta object
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    hostname = socket.gethostname()
    if os.path.exists(path):
        if timeout:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < datetime.datetime.now() - timeout:
                logger.info('Lock file "%s" has timed out.', path)
        else:
            return False
    with open(path, 'w') as fo:
        fo.write(hostname)
    logger.info('Lock file "%s" acquired.', path)
    return True


def release_lock(path):
    if os.path.exists(path):
        hostname = socket.gethostname()
        with open(path, 'r') as fo:
            content = fo.read()
        if content == hostname:
            os.remove(path)
            logger.info('Lock file "%s" released.', path)
        else:
            logger.info('Lock file "%s" is owned by another system: %s.', path, content)
            return False
    return True


def require_lock(path, timeout=None, silent=True):
    def _wrap(function):
        @wraps(function)
        def _wrapped_function(*args, **kwargs):
            if not acquire_lock(path, timeout):
                msg = 'Could not get lock "%s".' % path
                if silent:
                    logger.info(msg)
                else:
                    raise Exception(msg)
            else:
                try:
                    return function(*args, **kwargs)
                finally:
                    release_lock(path)
        return _wrapped_function
    return _wrap
