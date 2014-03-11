#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Rss utility functions
'''
# Django
from django.utils.tzinfo import LocalTimezone


# get_locale_tz_datetime function
#-----------------------------------------------------------------------------------
def get_locale_tz_datetime(dt):
    tz = LocalTimezone(dt)
    dt = dt.replace(tzinfo=tz)
    return dt

# get_RFC_2822_format function
#-----------------------------------------------------------------------------------
def get_RFC_2822_format(dt):
    if dt.tzinfo is None:
        dt = get_locale_tz_datetime(dt)
    return dt.strftime('%a, %d %b %Y %H:%M:%S %z')
    
