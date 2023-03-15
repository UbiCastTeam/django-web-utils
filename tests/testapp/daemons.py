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
        group='etc', name='hosts', label=_('Hosts file'), no_commands=True, only_conf=True, is_root=True,
        conf_path=Path('/etc/hosts'),
        help_text=_('Local hosts definitions.')
    ),
    dict(
        group='etc', name='fake', label=_('Fake daemon'),
        conf_path=Path('/etc/fake'), log_path=Path('/var/logs/fake.log'), pid_path=Path('/var/run/fake.pid'),
        help_text=_('Fake daemon.')
    ),
    dict(
        group='etc', name='dummy', label=_('Dummy daemon'),
        cls='testapp.daemons.DummyDaemon',
        help_text=_('Dummy daemon.')
    ),
]

GROUPS = [
    dict(name='etc', label=_('ETC')),
]
