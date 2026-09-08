from django.core.mail.backends.locmem import EmailBackend as LocMemEmailBackend


class FailingEmailBackend(LocMemEmailBackend):
    """
    Email backend used to test sending failures.
    Emails sent to an address containing "fail" are not delivered.
    """

    def send_messages(self, email_messages):
        for message in email_messages:
            if any('fail' in address for address in message.to):
                raise OSError('Simulated sending failure.')
        return super().send_messages(email_messages)


class UnavailableEmailBackend(LocMemEmailBackend):
    """
    Email backend used to test connection failures.
    """

    def open(self):
        raise OSError('Simulated connection failure.')
