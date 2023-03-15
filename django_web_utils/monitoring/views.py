import logging
import socket

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.utils.translation import gettext as _

from django_web_utils import json_utils
from django_web_utils import system_utils
from django_web_utils.monitoring import config, utils

logger = logging.getLogger('djwutils.monitoring.views')


@json_utils.json_view
@login_required
def check_password(request):
    if not request.user.is_superuser:
        return JsonResponse(error=_('You don\'t have the permission to access this url.'), code='perm', status=403)
    if request.method == 'POST':
        # Check that password is OK
        pwd = request.POST.get('data')
        if not pwd:
            return JsonResponse(dict(error=_('Please enter password.'), code='nopwd'), status=400)
        success, output = system_utils.execute_command('echo \'test\'', user='root', pwd=pwd)
        if success:
            request.session['pwd'] = pwd
            return JsonResponse(dict(pwd_ok=True))
        else:
            return JsonResponse(dict(error=_('Invalid password.'), code='wpwd'), status=400)
    else:
        pwd = request.session.get('pwd')
        return JsonResponse(dict(pwd_ok=bool(pwd)))


@login_required
def monitoring_panel(request):
    info = config.get_daemons_info()
    groups = []
    daemons_names = []
    for name in info.GROUPS_NAMES:
        group = dict(info.GROUPS[name])
        group['accessible_daemons'] = []
        for daemon in group['members']:
            if config.can_access_daemon(daemon, request):
                group['accessible_daemons'].append(daemon)
                daemons_names.append(daemon['name'])
        if group['accessible_daemons']:
            groups.append(dict(info.GROUPS[name]))
    if info.GROUPS_NAMES and not daemons_names:
        raise PermissionDenied()
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    tplt_data = dict(config.TEMPLATE_DATA) if config.TEMPLATE_DATA else {}
    tplt_data.update(dict(
        monitoring_page='panel',
        monitoring_body='monitoring/panel.html',
        monitoring_namespace=config.NAMESPACE,
        daemons_names=daemons_names,
        daemons_groups=groups,
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
        if not daemon or (not daemon.get('cls') and (command != 'clear_log' or not daemon.get('log_path'))):
            if all_daemons:
                continue
            success = False
            out = '%s %s' % (_('The daemon name is invalid:'), name)
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
def monitoring_log(request, name=None, path=None, owner='self', back_url=None):
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
        path = daemon['log_path'] if daemon.get('log_path') else (daemon['cls'].LOG_DIR / f'{name}.log')
        label = daemon.get('label')
        if daemon.get('is_root'):
            owner = 'root'
    if not label:
        label = path.name

    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    result = utils.log_view(request, path=path, owner=owner, date_adjust_fct=date_adjust_fct)
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


@login_required
def monitoring_config(request, name=None, path=None, owner='self', back_url=None):
    default_conf = None
    if not path:
        info = config.get_daemons_info()
        if name not in info.DAEMONS:
            raise Http404()
        daemon = info.DAEMONS[name]
        if not config.can_access_daemon(daemon, request):
            raise PermissionDenied()
        if request.method == 'POST' and not config.can_control_daemon(daemon, request):
            raise PermissionDenied()
        if daemon.get('cls'):
            path = daemon['cls'].get_conf_path()
            default_conf = daemon['cls'].DEFAULTS
            if 'LOGGING_LEVEL' not in default_conf:
                default_conf['LOGGING_LEVEL'] = 'INFO'
        else:
            path = daemon.get('conf_path')
        if daemon.get('is_root'):
            owner = 'root'
    if not path:
        raise Exception('No configuration path given.')
    if not name:
        name = path.name

    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    result = utils.edit_conf_view(request, path=path, default_conf=default_conf, owner=owner, date_adjust_fct=date_adjust_fct)
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    tplt_data = dict(config.TEMPLATE_DATA) if config.TEMPLATE_DATA else {}
    tplt_data.update(dict(
        monitoring_page='config',
        monitoring_body='monitoring/config.html',
        monitoring_namespace=config.NAMESPACE,
        title=_('Edit configuration file: %s') % name,
        back_url=back_url or reverse(config.NAMESPACE + ':monitoring-panel'),
        **result
    ))
    return render(request, tplt, tplt_data)
