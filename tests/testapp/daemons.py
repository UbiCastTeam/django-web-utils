from pathlib import Path

from django.utils.translation import gettext_lazy as _

from django_web_utils.daemon.base import BaseDaemon


class DummyDaemon(BaseDaemon):
    pass


def CAN_ACCESS(request):
    return request.user.is_superuser


def CAN_CONTROL(request):
    return request.user.is_superuser


DAEMONS = [
    dict(
        group='base', name='hosts', label=_('Hosts file'), no_commands=True, only_conf=True, is_root=True,
        conf_path=Path('/etc/hosts'),
        help_text=_('Local hosts definitions.')
    ),
    dict(
        group='base', name='apt', label=_('APT history'),
        log_path=Path('/var/log/apt/history.log'),
        help_text=_('APT history log.')
    ),
    dict(
        group='test', name='fake', label=_('Fake daemon'),
        conf_path=Path('/etc/fake'), log_path=Path('/var/log/fake.log'), pid_path=Path('/var/run/fake.pid'),
        help_text=_('Fake daemon.')
    ),
    dict(
        group='test', name='dummy', label=_('Dummy daemon'),
        cls='testapp.daemons.DummyDaemon',
        help_text=_('Dummy daemon.')
    ),
]

GROUPS = [
    dict(name='base', label=_('Base')),
    dict(name='test', label=_('Test')),
]
