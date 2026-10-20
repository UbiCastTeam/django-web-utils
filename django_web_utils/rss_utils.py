"""
Rss utility functions
"""
import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils.safestring import mark_safe

from . import html_utils


# get_locale_tz_datetime function
# ----------------------------------------------------------------------------
def get_locale_tz_datetime(dt):
    tz_name = getattr(settings, 'TIME_ZONE', None)
    tz = ZoneInfo(tz_name) if tz_name else datetime.UTC
    if dt.tzinfo is not None:
        # Aware dates are converted to keep the same instant
        return dt.astimezone(tz)
    return dt.replace(tzinfo=tz)


# get_rfc_2822_format function
# ----------------------------------------------------------------------------
def get_rfc_2822_format(dt):
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
        # The "]]>" sequence would end the CDATA section, so it is split in two sections
        xml = '<![CDATA[%s]]>' % xml.replace(']]>', ']]]]><![CDATA[>')
    return mark_safe(xml)  # noqa: S308 (text in a CDATA section)
