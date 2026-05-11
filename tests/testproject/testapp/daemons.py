from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django_web_utils.daemon.base import BaseDaemon


class DummyDaemon(BaseDaemon):
    pass


def CAN_ACCESS(request):  # noqa: N802
    return request.user.is_superuser


def CAN_CONTROL(request):  # noqa: N802
    return request.user.is_superuser


DAEMONS = [
    dict(
        group='base', name='hosts', label=_('Hosts file'), no_commands=True, only_conf=True, is_root=True,
        conf_path=Path('/etc/hosts'),
        help_text=_('Local hosts definitions.')
    ),
    dict(
        group='base', name='sample', label=_('Sample log'), only_log=True,
        log_path=Path(settings.BASE_DIR, 'storage/logs/sample.log'),
        help_text=_('Sample log file.')
    ),
    dict(
        group='test', name='fake', label=_('Fake daemon'),
        conf_path=Path('/etc/fake'), log_path=Path('/var/log/fake.log'), pid_path=Path('/var/run/fake.pid'),
        help_text=_('Fake daemon.')
    ),
    dict(
        group='test', name='dummy', label=_('Dummy daemon'),
        cls='testproject.testapp.daemons.DummyDaemon',
        help_text=_('Dummy daemon.')
    ),
]

GROUPS = [
    dict(name='base', label=_('Base')),
    dict(name='test', label=_('Test')),
]
