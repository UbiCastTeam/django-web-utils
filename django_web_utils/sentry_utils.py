import errno
import logging
import os
import time

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.types import Event, Hint

logger = logging.getLogger('djwutils.sentry_utils')


class ThrottledFilteredSentryReporter:
    """
    Class to filter and add a rate limit for error reports to Sentry.
    """
    def __init__(
        self,
        sentry_dsn: str,
        sentry_env: str,
        sentry_release: str,
        django_integration: bool = False,
        period_length_in_seconds: int = 24 * 3600,
        max_reports_in_period: int = 10,
        counter_cache_key: str = 'sentry_report_counter'
    ):
        self.period_length_in_seconds: int = period_length_in_seconds
        self.max_reports_in_period: int = max_reports_in_period
        self.counter_cache_key: str = counter_cache_key
        # Local counter used when the Django cache is not available
        self._local_counter: int = 0
        self._local_period_start: float | None = None

        integrations = [
            ExcepthookIntegration(),
            LoggingIntegration(
                sentry_logs_level=logging.INFO,  # Capture INFO and above as logs
                level=logging.INFO,  # Capture INFO and above as breadcrumbs
                event_level=logging.ERROR,  # Send ERROR records as events
            ),
        ]
        if django_integration:
            integrations.append(DjangoIntegration())

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=sentry_env or 'production',
            release=sentry_release,
            auto_enabling_integrations=False,
            default_integrations=False,
            integrations=integrations,
            before_send=self.before_send,
            send_default_pii=False,
        )

    def _get_cache(self) -> object | None:
        if hasattr(self, '_cache'):
            return self._cache
        try:
            from django.conf import ENVIRONMENT_VARIABLE, settings
            from django.core.cache import cache
        except ImportError:
            self._cache = None
            return None
        # The Django cache cannot be used if Django is not configured (for example in scripts).
        # Settings are loaded lazily, so they are considered as configured if the settings module is defined.
        if not settings.configured and not os.environ.get(ENVIRONMENT_VARIABLE):
            # The result is not stored because Django can be configured later
            return None
        self._cache = cache
        return cache

    def increment_counter(self) -> int:
        cache = self._get_cache()
        if cache is None:
            # Use a counter local to the current process
            now = time.monotonic()
            if self._local_period_start is None or now - self._local_period_start > self.period_length_in_seconds:
                self._local_period_start = now
                self._local_counter = 0
            self._local_counter += 1
            return self._local_counter
        try:
            value = cache.incr(self.counter_cache_key)
        except ValueError:
            cache.set(self.counter_cache_key, 1, timeout=self.period_length_in_seconds)
            value = 1
        return value

    def before_send(self, event: Event, hint: Hint) -> Event | None:
        # Sentry doc: https://docs.sentry.io/platforms/python/configuration/filtering/

        # Apply filters
        # The "exc_info" value is a tuple like the one returned by "sys.exc_info()": (type, value, traceback)
        exc_info = hint.get('exc_info') or (None, None, None)
        exc_type, exc_value = exc_info[0], exc_info[1]
        if exc_type is not None:
            if exc_type.__name__ == 'UnreadablePostError':
                # Ignore UWSGI connection errors (UnreadablePostError)
                # Like:
                #     UnreadablePostError: error during read(---) on wsgi.input
                return None
            if exc_type.__name__ == 'OperationalError':
                # Ignore database connection errors (OperationalError)
                # Like:
                #     OperationalError: could not connect to server: Connection refused
                #     OperationalError: server closed the connection unexpectedly
                #     OperationalError: SSL SYSCALL error: EOF detected
                return None
            if isinstance(exc_value, OSError) and exc_value.errno == errno.ENOSPC:
                # Ignore no space left errors (OSError)
                # Like:
                #     OSError [Errno 28] No space left on device: ...
                return None

        # Rate limit
        try:
            counter = self.increment_counter()
        except Exception as err:
            logger.warning(
                'Failed to increment counter of Sentry error reports, nothing will be sent. Details: %s',
                err
            )
            return None
        if counter > self.max_reports_in_period:
            logger.warning(
                'Reached rate limit of Sentry error reports (%s reports in %s seconds), nothing will be sent.',
                self.max_reports_in_period, self.period_length_in_seconds
            )
            return None

        return event
