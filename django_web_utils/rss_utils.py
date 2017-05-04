#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Rss utility functions
'''
import pytz

from django.conf import settings


# get_locale_tz_datetime function
# ----------------------------------------------------------------------------
def get_locale_tz_datetime(dt):
    tz_name = getattr(settings, 'TIME_ZONE', None)
    if tz_name:
        tz = pytz.timezone(tz_name)
    else:
        tz = pytz.utc
    dt = tz.localize(dt)
    return dt


# get_RFC_2822_format function
# ----------------------------------------------------------------------------
def get_RFC_2822_format(dt):
    if dt.tzinfo is None:
        dt = get_locale_tz_datetime(dt)
    return dt.strftime('%a, %d %b %Y %H:%M:%S %z')
