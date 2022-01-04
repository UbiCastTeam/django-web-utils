from django.utils.translation import gettext_lazy as _


def CAN_ACCESS(request):
    return request.user.is_superuser


def CAN_CONTROL(request):
    return request.user.is_superuser


DAEMONS = [
    dict(
        group='etc', name='hosts', label=_('Hosts file'), no_commands=True, only_conf=True, is_root=True,
        conf_path='/etc/hosts',
        help_text=_('Local hosts definitions.')
    ),
    dict(
        group='etc', name='fake', label=_('Fake'),
        conf_path='/etc/fake', log_path='/var/logs/fake.log', pid_path='/var/run/fake.pid',
        help_text=_('Fake daemon.')
    ),
]

GROUPS = [
    dict(name='etc', label=_('ETC')),
]
