#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
System information
'''
import os
import re
import subprocess
import sys
# Django
from django.utils.translation import gettext_lazy as _
import django
# django_web_utils
from django_web_utils.packages_utils import get_version


def _additional_translations():
    # Translations for lsb_release -a
    _('Distributor ID')
    _('Description')
    _('Release')
    _('Codename')


def _get_output(cmd):
    env = dict(os.environ)
    env['LANG'] = 'C.UTF-8'
    env['LC_ALL'] = 'C.UTF-8'
    try:
        p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
    except Exception as e:
        return str(e).strip()
    return p.stdout.strip()


def get_system_info(package=None, module=None, extra=None):
    # This function returns data for the sysinfo.html template
    tplt_args = dict(info_sections=list())
    # Project version
    version, revision, local_repo = get_version(package, module)
    tplt_args['info_package'] = []
    tplt_args['info_package'].append(dict(label=_('Version'), value=version))
    tplt_args['info_package'].append(dict(label=_('Revision'), value=revision))
    tplt_args['info_package'].append(dict(label=_('Python version'), value=sys.version))
    dj_version = getattr(django, 'VERSION', '?')
    if isinstance(dj_version, tuple):
        dj_version = '.'.join([str(i) for i in dj_version])
    tplt_args['info_package'].append(dict(label=_('Django version'), value=dj_version))
    try:
        from django.conf import settings
        db_engine = ', '.join([db['ENGINE'] for db in settings.DATABASES.values()])
        time_zone = getattr(settings, 'TIME_ZONE', '?')
    except Exception:
        pass
    else:
        tplt_args['info_package'].append(dict(label=_('Database engine'), value=db_engine))
        tplt_args['info_package'].append(dict(label=_('Django time zone'), value=time_zone))
    tplt_args['local_repo'] = local_repo
    tplt_args['version'] = version
    tplt_args['revision'] = revision
    tplt_args['info_sections'].append(dict(label=_('Software'), info=tplt_args['info_package']))
    # OS info
    tplt_args['info_os'] = []
    tplt_args['info_os'].append(dict(label=_('Time zone'), value=_get_output(['cat', '/etc/timezone'])))
    tplt_args['info_os'].append(dict(label=_('Uptime'), value=_get_output(['uptime', '-p'])))
    tplt_args['info_os'].append(dict(label=_('Load'), value=_get_output(['cat', '/proc/loadavg'])))
    tplt_args['info_os'].append(dict(label=_('Kernel'), value=_get_output(['uname', '-r'])))
    tplt_args['info_os'].append(dict(label=_('Hostname'), value=_get_output(['uname', '-n'])))
    tplt_args['info_os'].append(dict(label=_('Platform'), value=_get_output(['uname', '-i'])))
    for line in _get_output(['lsb_release', '-a']).split('\n'):
        if ':' in line:
            index = line.index(':')
            field = line[:index].strip()
            value = line[index + 1:].strip()
            # Field is translated in _additional_translations
            tplt_args['info_os'].append(dict(label=_(field), value=value))
    tplt_args['info_sections'].append(dict(label=_('OS'), info=tplt_args['info_os']))
    # HDD
    dfh = _get_output(['df', '-h']).strip()
    if dfh:
        tplt_args['info_hdd'] = []
        for value in dfh.split('\n'):
            tplt_args['info_hdd'].append(dict(label='', value=value))
        tplt_args['info_sections'].append(dict(label=_('HDD'), info=tplt_args['info_hdd']))
    # CPU
    cpuinfo_file = _get_output(['cat', '/proc/cpuinfo'])
    cpuinfo = {'total cores': 0}
    for line in cpuinfo_file.split('\n'):
        if ':' in line:
            if line.startswith('processor'):
                cpuinfo['total cores'] += 1
            else:
                index = line.index(':')
                field = line[:index].strip()
                value = line[index + 1:].strip()
                cpuinfo[field] = value
    if cpuinfo.get('cpu MHz'):
        # Change unit to GHz to have same unit as default freq
        try:
            value = float(cpuinfo['cpu MHz'])
            cpuinfo['current freq'] = '%.2f GHz' % (value / 1000)
        except ValueError:
            pass
    cpuinfo['model name'] = ' '.join(cpuinfo.get('model name', '').split())
    if '@' in cpuinfo.get('model name', ''):
        # Try to get default frequency
        index = cpuinfo['model name'].index('@')
        cpuinfo['default freq'] = cpuinfo['model name'][index + 1:].strip().replace('GHz', ' GHz')
        cpuinfo['model name'] = cpuinfo['model name'][:index].strip()
    tplt_args['cpuinfo'] = cpuinfo
    tplt_args['info_cpu'] = []
    tplt_args['info_cpu'].append(dict(label=_('Model'), value=cpuinfo.get('model name', '?')))
    tplt_args['info_cpu'].append(dict(label=_('Cores'), value=cpuinfo['total cores'] or '?'))
    tplt_args['info_cpu'].append(dict(label=_('Default frequency'), value=cpuinfo.get('default freq', '?')))
    tplt_args['info_cpu'].append(dict(label=_('Current frequency'), value=cpuinfo.get('current freq', '?')))
    tplt_args['info_sections'].append(dict(label=_('CPU'), info=tplt_args['info_cpu']))
    # GPU
    tplt_args['info_gpu'] = []
    gpu_model = None
    lspci = _get_output(['lspci'])
    if 'VGA' in lspci:
        vga_re = re.search(r'.+VGA.+:(.+)', lspci)
        gpu_model = vga_re.groups()[0].strip()
        if len(gpu_model) > 60 and '\n' not in gpu_model:
            # add line return
            min_ind = int(len(gpu_model) / 2) - 10
            index = gpu_model[min_ind:].find(' ')
            if index >= 0:
                gpu_model = gpu_model[:min_ind + index] + '\n' + gpu_model[min_ind + index + 1:]
    tplt_args['info_gpu'].append(dict(label=_('Model'), value=gpu_model or '?'))
    tplt_args['info_sections'].append(dict(label=_('GPU'), info=tplt_args['info_gpu']))
    # Memory
    meminfo_file = _get_output(['cat', '/proc/meminfo'])
    tplt_args['info_memory'] = []
    try:
        mem_dict = dict()
        for line in meminfo_file.split('\n'):
            key, value = line.rstrip(' kB').split(':')
            try:
                value = int(value.strip())
            except ValueError:
                continue
            mem_dict[key.strip()] = value
        tplt_args['info_memory'].append(dict(label=_('Total'), value='%.2f %s' % ((mem_dict.get('MemTotal', 0) / 1000000.), _('GB'))))
        tplt_args['info_memory'].append(dict(label=_('Free'), value='%.2f %s' % ((mem_dict.get('MemFree', 0) / 1000000.), _('GB'))))
        tplt_args['info_memory'].append(dict(label=_('Cached'), value='%.2f %s' % ((mem_dict.get('Cached', 0) / 1000000.), _('GB'))))
    except Exception as e:
        tplt_args['info_memory'].append(dict(label=_('Failed to get information'), value=e))
    tplt_args['info_sections'].append(dict(label=_('Memory'), info=tplt_args['info_memory']))
    # Network
    ipaddr = _get_output(['ip', 'addr']).strip()
    if ipaddr:
        tplt_args['info_network'] = []
        for value in ipaddr.split('\n'):
            tplt_args['info_network'].append(dict(label='', value=value))
        tplt_args['info_sections'].append(dict(label=_('Network'), info=tplt_args['info_network']))
    # Sensors
    sensors = _get_output(['sensors']).strip()
    if sensors:
        tplt_args['info_sensors'] = []
        for value in sensors.split('\n\n'):
            tplt_args['info_sensors'].append(dict(label='', value=value))
        tplt_args['info_sections'].append(dict(label=_('Sensors'), info=tplt_args['info_sensors']))
    # Extra data
    if extra:
        for section, values in extra.items():
            if section in tplt_args:
                tplt_args[section].extend(values)
            else:
                tplt_args[section] = values
    return tplt_args
