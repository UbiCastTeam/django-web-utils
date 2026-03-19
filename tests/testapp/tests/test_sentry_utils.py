import errno
from unittest.mock import patch

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
    fake_hint = {'exc_info': (ValueError, 'nope')}
    for i in range(12):
        event = sentry_reporter.before_send(fake_event, fake_hint)
        if i < 10:
            assert event == fake_event, f'Failed on loop {i}'
        else:
            assert event is None, f'Failed on loop {i}'


@pytest.mark.parametrize('exc_class_name, exc_class_arg, report_expected', [
    pytest.param('ValueError', {}, True, id='ValueError'),
    pytest.param('UnreadablePostError', {}, False, id='UnreadablePostError'),
    pytest.param('OperationalError', {}, False, id='OperationalError'),
    pytest.param('OSError', {'errno': errno.ENOENT}, True, id='OSError'),
    pytest.param('OSError', {'errno': errno.ENOSPC}, False, id='OSError-NoSpace'),
])
def test_exc_filter(sentry_reporter, exc_class_name, exc_class_arg, report_expected):

    class FakeError():
        pass

    FakeError.__name__ = exc_class_name
    for key, val in exc_class_arg.items():
        setattr(FakeError, key, val)

    fake_event = 'event'
    fake_hint = {'exc_info': (FakeError, 'nope')}
    event = sentry_reporter.before_send(fake_event, fake_hint)
    if report_expected:
        assert event == fake_event
    else:
        assert event is None
