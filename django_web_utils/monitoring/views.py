#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
logger = logging.getLogger('djwutils.monitoring.views')
# Django
from django.shortcuts import render
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
# Django web utils
from django_web_utils import json_utils
from django_web_utils.monitoring import config, utils


@config.view_decorator
def monitoring_panel(request):
    info = config.info_module
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    return render(request, tplt, dict(
        monitoring_page='panel',
        monitoring_body='monitoring/panel.html',
        daemons_names=getattr(info, 'DAEMONS_NAMES', None),
        daemons_groups=getattr(info, 'DAEMONS_GROUPS', None),
    ))


@config.view_decorator
def monitoring_status(request):
    info = config.info_module
    DAEMONS = getattr(info, 'DAEMONS', dict())
    has_access = getattr(info, 'has_access', None)
    if has_access and not has_access(request):
        raise PermissionDenied()

    name = request.GET.get('name')
    if name and name in DAEMONS:
        target = {name: DAEMONS[name]}
    else:
        target = DAEMONS
    data = utils.daemons_statuses(target, date_adjust_fct=request.user.get_locale_date)
    return json_utils.success_response(**data)


@config.view_decorator
def monitoring_command(request):
    info = config.info_module
    DAEMONS = getattr(info, 'DAEMONS', dict())
    command = request.POST.get('cmd')
    name = request.POST.get('daemon')
    if name == 'all':
        all_daemons = True
        names = DAEMONS.keys()
        names.sort()
    else:
        if name not in DAEMONS:
            raise Http404()
        all_daemons = False
        names = [name]
    
    message = u''
    for name in names:
        daemon = DAEMONS.get(name)
        if message:
            message += u'\n\n'
        if not daemon or (not daemon.get('daemon_class') and (command != 'clear_log' or not daemon.get('log_path'))):
            if all_daemons:
                continue
            success = False
            msg = u'%s %s' % (_('Invalid daemon name:'), name)
        else:
            if command == 'clear_log':
                path = daemon['log_path'] if daemon.get('log_path') else os.path.join(daemon['daemon_class'].LOG_DIR, '%s.log' % name)
                success, msg = utils.clear_log(path)
            elif command in ('start', 'restart') and daemon.get('only_stop'):
                continue
            else:
                success, msg = utils.execute_daemon_command(daemon['daemon_class'], command)
        if success:
            message += u'%s\n%s' % (_('Command "%(cmd)s" on "%(name)s" successfully executed.') % dict(cmd=command, name=name), msg)
        else:
            message += u'%s\n%s' % (_('Command "%(cmd)s" on "%(name)s" failed.') % dict(cmd=command, name=name), msg)
    return json_utils.success_response(message=message)


@config.view_decorator
def monitoring_log(request, name=None, path=None):
    label = None
    if not path:
        info = config.info_module
        DAEMONS = getattr(info, 'DAEMONS', dict())
        if name not in DAEMONS:
            raise Http404()
        daemon = DAEMONS[name]
        path = daemon['log_path'] if daemon.get('log_path') else os.path.join(daemon['daemon_class'].LOG_DIR, '%s.log' % name)
        label = daemon.get('label')
    if not label:
        label = os.path.basename(path)

    result = utils.log_view(
        request,
        path=path,
        date_adjust_fct=request.user.get_locale_date,
    )
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    return render(request, tplt, dict(
        monitoring_page='log',
        monitoring_body='monitoring/log.html',
        title=u'%s - %s' % (label, _('log file')),
        **result
    ))


@config.view_decorator
def monitoring_config(request, name):
    info = config.info_module
    DAEMONS = getattr(info, 'DAEMONS', dict())
    if name not in DAEMONS:
        raise Http404()
    
    daemon = DAEMONS[name]
    if not daemon.get('daemon_class'):
        raise Exception('Unable to find daemon module %s.' % name)

    result = utils.edit_conf_view(
        request,
        daemon=daemon['daemon_class'],
        date_adjust_fct=request.user.get_locale_date,
    )
    if not isinstance(result, dict):
        return result
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'monitoring/base.html'
    return render(request, tplt, dict(
        monitoring_page='config',
        monitoring_body='monitoring/config.html',
        title=_('Edit daemon configuration: %s') % name,
        **result
    ))
