import datetime
from zoneinfo import ZoneInfo

import pytest

from django_web_utils import rss_utils


@pytest.mark.parametrize('time_zone, expected', [
    ('Europe/Paris', 'Mon, 02 Feb 2026 03:04:05 +0100'),
    ('UTC', 'Mon, 02 Feb 2026 03:04:05 +0000'),
    (None, 'Mon, 02 Feb 2026 03:04:05 +0000'),
])
def test_rfc_2822_format__naive(settings, time_zone, expected):
    settings.TIME_ZONE = time_zone
    assert rss_utils.get_rfc_2822_format(datetime.datetime(2026, 2, 2, 3, 4, 5)) == expected


def test_rfc_2822_format__aware():
    dt = datetime.datetime(2026, 7, 2, 3, 4, 5, tzinfo=ZoneInfo('Europe/Paris'))
    assert rss_utils.get_rfc_2822_format(dt) == 'Thu, 02 Jul 2026 03:04:05 +0200'


@pytest.mark.parametrize('time_zone, expected', [
    ('Europe/Paris', datetime.datetime(2026, 2, 2, 4, 4, 5)),
    ('UTC', datetime.datetime(2026, 2, 2, 3, 4, 5)),
    (None, datetime.datetime(2026, 2, 2, 3, 4, 5)),
])
def test_locale_tz_datetime__aware(settings, time_zone, expected):
    settings.TIME_ZONE = time_zone
    dt = datetime.datetime(2026, 2, 2, 3, 4, 5, tzinfo=datetime.UTC)
    result = rss_utils.get_locale_tz_datetime(dt)
    # The instant must not change
    assert result == dt
    assert result.replace(tzinfo=None) == expected


def test_rfc_2822_format__empty():
    assert rss_utils.get_rfc_2822_format(None) == ''


@pytest.mark.parametrize('text, expected', [
    ('', ''),
    ('  <p>Some &amp; text</p> ', '<![CDATA[Some & text]]>'),
    ('a ]]> <script>b</script>', '<![CDATA[a ]]]]><![CDATA[>]]>'),
    ('a ]]&gt; b', '<![CDATA[a ]]]]><![CDATA[> b]]>'),
])
def test_xml_for_text(text, expected):
    assert rss_utils.get_xml_for_text(text) == expected
