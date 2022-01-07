#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Time utility functions
"""
from typing import Tuple


def get_hms_tuple(seconds: int) -> Tuple[int, int, int]:
    """
    Returns hours, minutes and seconds from a number of seconds.
    :param seconds: positive integer
    """
    if seconds < 0:
        raise ValueError(f'seconds argument must be a positive integer ({seconds}).')
    seconds = int(seconds)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return hours, minutes, seconds


def get_hms_str(seconds: int) -> str:
    """
    Returns a string with the format '[%dh ][%dm ]%ds'.
    :param seconds: positive integer
    """
    hours, minutes, seconds = get_hms_tuple(seconds)
    if hours > 0:
        return f'{hours}h {minutes}m {seconds}s'
    elif minutes > 0:
        return f'{minutes}m {seconds}s'
    else:
        return f'{seconds}s'
