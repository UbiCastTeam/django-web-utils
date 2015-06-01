#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
logger = logging.getLogger('djwutils.monitoring.views')
# Django
from django.shortcuts import render
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
# Django web utils
from django_web_utils import json_utils
from django_web_utils.monitoring import config, utils


@login_required
def monitoring_panel(request):
    info = config.get_daemons_info()
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    groups = list()
    daemons_names = list()
    for name in info.GROUPS_NAMES:
        group = dict(info.GROUPS[name])
        group['accessible_daemons'] = list()
        for daemon in group['members']:
            if config.can_access_daemon(daemon, request):
                group['accessible_daemons'].append(daemon)
                daemons_names.append(daemon['name'])
        if group['accessible_daemons']:
            groups.append(dict(info.GROUPS[name]))
    if info.GROUPS_NAMES and not daemons_names:
        raise PermissionDenied()
    return render(request, tplt, dict(
        monitoring_page='panel',
        monitoring_body='monitoring/panel.html',
        daemons_names=daemons_names,
        daemons_groups=groups,
    ))


@login_required
def monitoring_status(request):
    info = config.get_daemons_info()
    name = request.GET.get('name')
    if name and name in info.DAEMONS:
        targets = [name]
    else:
        targets = info.DAEMONS_NAMES
    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    data = dict()
    for name in targets:
        daemon = info.DAEMONS[name]
        if not config.can_access_daemon(daemon, request):
            raise PermissionDenied()
        data[name] = utils.get_daemon_status(request, daemon, date_adjust_fct=date_adjust_fct)
    return json_utils.success_response(**data)


@json_utils.json_view(methods='POST')
@login_required
def monitoring_command(request):
    info = config.get_daemons_info()
    command = request.POST.get('cmd')
    name = request.POST.get('daemon')
    if name == 'all':
        all_daemons = True
        names = info.DAEMONS.keys()
        names.sort()
    else:
        if name not in info.DAEMONS:
            raise Http404()
        all_daemons = False
        names = [name]
    
    message = u''
    for name in names:
        daemon = info.DAEMONS.get(name)
        if not config.can_control_daemon(daemon, request):
            raise PermissionDenied()
        if not daemon or (not daemon.get('cls') and (command != 'clear_log' or not daemon.get('log_path'))):
            if all_daemons:
                continue
            success = False
            msg = u'%s %s' % (_('Invalid daemon name:'), name)
        else:
            if command in ('start', 'restart') and daemon.get('only_stop'):
                continue
            else:
                success, msg = utils.execute_daemon_command(request, daemon, command)
        if success:
            text = _('Command "%(cmd)s" on "%(name)s" successfully executed.')
        else:
            text = _('Command "%(cmd)s" on "%(name)s" failed.')
        message += u'<div class="success">%s</div>' % escape(unicode(text % dict(cmd=command, name=name)))
        if msg:
            message += u'<div>%s</div>' % escape(msg)
    return json_utils.success_response(message=message)


@login_required
def monitoring_log(request, name=None, path=None):
    label = None
    if not path:
        info = config.get_daemons_info()
        if name not in info.DAEMONS:
            raise Http404()
        daemon = info.DAEMONS[name]
        if not config.can_access_daemon(daemon, request):
            raise PermissionDenied()
        if request.method == 'POST' and not config.can_control_daemon(daemon, request):
            raise PermissionDenied()
        path = daemon['log_path'] if daemon.get('log_path') else os.path.join(daemon['cls'].LOG_DIR, '%s.log' % name)
        label = daemon.get('label')
    if not label:
        label = os.path.basename(path)

    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    result = utils.log_view(request, path=path, date_adjust_fct=date_adjust_fct)
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    return render(request, tplt, dict(
        monitoring_page='log',
        monitoring_body='monitoring/log.html',
        title=u'%s - %s' % (label, _('log file')),
        back_url=reverse('monitoring-panel'),
        **result
    ))


@login_required
def monitoring_config(request, name=None, path=None):
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
    if not path:
        raise Exception('No configuration path given.')

    date_adjust_fct = config.DATE_ADJUST_FCT(request) if config.DATE_ADJUST_FCT else None
    result = utils.edit_conf_view(request, path=path, default_conf=default_conf, date_adjust_fct=date_adjust_fct)
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    return render(request, tplt, dict(
        monitoring_page='config',
        monitoring_body='monitoring/config.html',
        title=_('Edit daemon configuration: %s') % name,
        back_url=reverse('monitoring-panel'),
        **result
    ))
