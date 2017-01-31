#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Django
from django.conf import settings


# Take a look at the readme file for settings descriptions

def _import(module):
    if not isinstance(module, str):
        return module
    elif '.' in module:
        element = module.split('.')[-1]
        _tmp = __import__(module[:-len(element) - 1], fromlist=[element])
        return getattr(_tmp, element)
    else:
        return __import__(module)


class _Info(object):
    pass


BASE_TEMPLATE = getattr(settings, 'MONITORING_BASE_TEMPLATE', None)

TEMPLATE_DATA = getattr(settings, 'MONITORING_TEMPLATE_DATA', None)

DATE_ADJUST_FCT = getattr(settings, 'MONITORING_DATE_ADJUST_FCT', None)


def get_daemons_info():
    if '_daemons_info' not in globals():
        cleaned_info = _Info()
        cleaned_info.DAEMONS = dict()
        cleaned_info.DAEMONS_NAMES = list()
        cleaned_info.GROUPS = dict()
        cleaned_info.GROUPS_NAMES = list()
        info_module = getattr(settings, 'MONITORING_DAEMONS_INFO', None)
        if info_module:
            info_module = _import(info_module)
            for group in getattr(info_module, 'GROUPS', list()):
                group['members'] = list()
                group['rowspan'] = 0
                cleaned_info.GROUPS[group['name']] = group
                cleaned_info.GROUPS_NAMES.append(group['name'])
            for daemon in getattr(info_module, 'DAEMONS', list()):
                cleaned_info.DAEMONS_NAMES.append(daemon['name'])
                cleaned_info.DAEMONS[daemon['name']] = daemon
                if daemon.get('cls'):
                    daemon['cls'] = _import(daemon['cls'])
                    daemon['conf_path'] = daemon['cls'].get_conf_path()
                    daemon['log_path'] = daemon['cls'].get_log_path()
                if not daemon.get('can_access'):
                    daemon['can_access'] = getattr(info_module, 'CAN_ACCESS', lambda request: request.user.is_superuser)
                if not daemon.get('can_control'):
                    daemon['can_control'] = getattr(info_module, 'CAN_CONTROL', lambda request: request.user.is_superuser)
                cleaned_info.GROUPS[daemon['group']]['members'].append(daemon)
                cleaned_info.GROUPS[daemon['group']]['rowspan'] += 2
        globals()['_daemons_info'] = cleaned_info
    return globals()['_daemons_info']


def can_access_daemon(daemon, request):
    return daemon['can_access'](request)


def can_control_daemon(daemon, request):
    if not can_access_daemon(daemon, request):
        return False
    return daemon['can_control'](request)
