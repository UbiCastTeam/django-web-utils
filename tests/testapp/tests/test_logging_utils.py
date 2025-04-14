import logging

from django.core import mail

from django_web_utils.logging_utils import ThrottledAdminEmailHandler


def test_limit():
    handler = ThrottledAdminEmailHandler()
    for i in range(15):
        record = logging.LogRecord(
            name='app.test', level=logging.INFO, pathname='app/test.py',
            lineno=10, msg='The message', args={}, exc_info=None
        )
        handler.emit(record)
    mailinbox = [m.to[0] for m in mail.outbox]
    assert mailinbox == 10 * ['admin@example.com']
