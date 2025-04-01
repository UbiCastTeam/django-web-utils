import logging
import socket

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _

from django_web_utils import json_utils
from django_web_utils.monitoring import config, utils

logger = logging.getLogger('djwutils.monitoring.views')


@login_required
def monitoring_panel(request):
    info = config.get_daemons_info()
    if not info.GROUPS_NAMES:
        raise Http404()
    groups = []
    show_top_controls = False
    for name in info.GROUPS_NAMES:
        group = dict(info.GROUPS[name])
        group['daemons'] = []
        for member in group['members']:
            if config.can_access_daemon(member, request):
                daemon = dict(member)
                daemon['show_controls'] = config.can_control_daemon(member, request)
                if daemon['show_controls']:
                    show_top_controls = True
                group['daemons'].append(daemon)
        if group['daemons']:
            groups.append(group)
    if not groups:
        raise PermissionDenied()
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    tplt_data = dict(config.TEMPLATE_DATA) if config.TEMPLATE_DATA else {}
    tplt_data.update(dict(
        monitoring_page='panel',
        monitoring_body='monitoring/panel.html',
        monitoring_namespace=config.NAMESPACE,
        daemons_groups=groups,
        show_top_controls=show_top_controls,
        hostname=socket.gethostname(),
    ))
    return render(request, tplt, tplt_data)


@json_utils.json_view(methods='GET')
@login_required
def monitoring_status(request):
    info = config.get_daemons_info()
    name = request.GET.get('name')
    if name and name in info.DAEMONS:
        targets = [name]
    else:
        targets = info.DAEMONS_NAMES
    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    data = {}
    for name in targets:
        daemon = info.DAEMONS[name]
        if not config.can_access_daemon(daemon, request):
            raise PermissionDenied()
        data[name] = utils.get_daemon_status(request, daemon, date_adjust_fct=date_adjust_fct)
    return JsonResponse(data)


@json_utils.json_view(methods='POST')
@login_required
def monitoring_command(request):
    info = config.get_daemons_info()
    command = request.POST.get('cmd')
    name = request.POST.get('daemon')
    if name == 'all':
        all_daemons = True
        names = list(info.DAEMONS.keys())
        names.sort()
    else:
        if name not in info.DAEMONS:
            raise Http404()
        all_daemons = False
        names = [name]

    msgs = []
    for name in names:
        daemon = info.DAEMONS.get(name)
        if not config.can_control_daemon(daemon, request):
            raise PermissionDenied()
        if not daemon or not daemon.get('cls'):
            if all_daemons:
                continue
            success = False
            out = '%s "%s"' % (_('The daemon name is invalid:'), name)
        else:
            if command in ('start', 'restart') and daemon.get('only_stop'):
                continue
            else:
                success, out = utils.execute_daemon_command(request, daemon, command)
        if success:
            text = _('The command "%(cmd)s" on "%(name)s" was successfully executed.')
        else:
            text = _('The command "%(cmd)s" on "%(name)s" has failed.')
        msgs.append(dict(
            name=name,
            level='success' if success else 'error',
            text=text % dict(cmd=command, name=name),
            out=out,
        ))
    return JsonResponse(dict(messages=msgs))


@login_required
def monitoring_log(request, name=None, path=None, back_url=None):
    label = None
    can_control = True
    if not path:
        info = config.get_daemons_info()
        if name not in info.DAEMONS:
            raise Http404()
        daemon = info.DAEMONS[name]
        if not config.can_access_daemon(daemon, request):
            raise PermissionDenied()
        can_control = config.can_control_daemon(daemon, request)
        if request.method == 'POST' and not can_control:
            raise PermissionDenied()
        if daemon.get('cls'):
            path = daemon['cls'].LOG_DIR / f'{name}.log'
        else:
            path = daemon.get('log_path')
        label = daemon.get('label')
    if not path:
        raise Http404()
    if not label:
        label = path.name

    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    result = utils.log_view(request, path=path, rotated_access=True, date_adjust_fct=date_adjust_fct)
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    tplt_data = dict(config.TEMPLATE_DATA) if config.TEMPLATE_DATA else {}
    tplt_data.update(dict(
        monitoring_page='log',
        monitoring_body='monitoring/log.html',
        monitoring_namespace=config.NAMESPACE,
        title='%s - %s' % (label, _('log file')),
        back_url=back_url or reverse(config.NAMESPACE + ':monitoring-panel'),
        can_control=can_control,
        hostname=socket.gethostname(),
        **result
    ))
    return render(request, tplt, tplt_data)
