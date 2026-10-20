import errno
from unittest.mock import patch, PropertyMock

import pytest

from django_web_utils.sentry_utils import ThrottledFilteredSentryReporter


@pytest.fixture()
def sentry_reporter():
    with patch('sentry_sdk.init', return_value=None):
        yield ThrottledFilteredSentryReporter(
            sentry_dsn='mock',
            sentry_env='test',
            sentry_release='1.0'
        )


def test_no_exc_info(sentry_reporter):
    fake_event = 'event'
    fake_hint = {}
    event = sentry_reporter.before_send(fake_event, fake_hint)
    assert event == fake_event


def test_limit(sentry_reporter):
    fake_event = 'event'
    fake_hint = {'exc_info': (ValueError, ValueError('nope'), None)}
    for i in range(12):
        event = sentry_reporter.before_send(fake_event, fake_hint)
        if i < 10:
            assert event == fake_event, f'Failed on loop {i}'
        else:
            assert event is None, f'Failed on loop {i}'


class UnreadablePostError(Exception):
    pass


class OperationalError(Exception):
    pass


@pytest.mark.parametrize('error, report_expected', [
    pytest.param(ValueError('nope'), True, id='ValueError'),
    pytest.param(UnreadablePostError('nope'), False, id='UnreadablePostError'),
    pytest.param(OperationalError('nope'), False, id='OperationalError'),
    pytest.param(OSError(errno.ENOENT, 'nope'), True, id='OSError'),
    pytest.param(OSError(errno.ENOSPC, 'No space left on device'), False, id='OSError-NoSpace'),
    pytest.param(FileNotFoundError(errno.ENOENT, 'nope'), True, id='FileNotFoundError'),
])
def test_exc_filter(sentry_reporter, error, report_expected):
    fake_event = 'event'
    fake_hint = {'exc_info': (type(error), error, None)}
    event = sentry_reporter.before_send(fake_event, fake_hint)
    if report_expected:
        assert event == fake_event
    else:
        assert event is None


def test_limit__without_django_cache(sentry_reporter):
    # The rate limit must work even if the Django cache is not available
    sentry_reporter._cache = None
    fake_event = 'event'
    fake_hint = {'exc_info': (ValueError, ValueError('nope'), None)}
    results = [sentry_reporter.before_send(fake_event, fake_hint) for i in range(12)]
    assert results == [fake_event] * 10 + [None] * 2


def test_get_cache__django_configured_later(sentry_reporter, monkeypatch):
    from django.conf import LazySettings
    from django.core.cache import cache

    monkeypatch.delenv('DJANGO_SETTINGS_MODULE', raising=False)
    with patch.object(LazySettings, 'configured', new_callable=PropertyMock, return_value=False):
        assert sentry_reporter._get_cache() is None
    # The Django cache must be used once Django is configured
    assert sentry_reporter._get_cache() is cache
