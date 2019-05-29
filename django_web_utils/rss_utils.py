#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Rss utility functions
'''
import pytz

from django.conf import settings
from django.utils.safestring import mark_safe

from . import html_utils


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
    if not dt:
        return ''
    if dt.tzinfo is None:
        dt = get_locale_tz_datetime(dt)
    return dt.strftime('%a, %d %b %Y %H:%M:%S %z')


# get_xml_for_text function
# ----------------------------------------------------------------------------
def get_xml_for_text(text):
    xml = text.strip()
    if xml:
        xml = html_utils.unescape(xml)
        xml = '<![CDATA[%s]]>' % xml
    return mark_safe(xml)
