#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
System information
'''
import os
import subprocess
import datetime
import logging
logger = logging.getLogger('djwutils.monitoring.sysinfo')
# Django
import django
from django.utils.translation import ugettext_lazy as _


def _additional_translations():
    # Translations for lsb_release -a
    _('Distributor ID')
    _('Description')
    _('Release')
    _('Codename')


def _get_output(cmd):
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=not isinstance(cmd, list))
        out, err = p.communicate()
    except OSError:
        return ''
    else:
        return ((str(out, 'utf-8') if out else '') + (str(err, 'utf-8') if err else '')).strip()


def get_version(package=None, module=None):
    version = ''
    revision = ''
    if module:
        version = getattr(module, '__version__', '')
        git_dir = module.__path__[0]
        if os.path.islink(git_dir):
            git_dir = os.readlink(git_dir)
        if not os.path.exists(os.path.join(git_dir, '.git')):
            git_dir = os.path.dirname(git_dir)
            if not os.path.exists(os.path.join(git_dir, '.git')):
                git_dir = os.path.dirname(git_dir)
        git_dir = os.path.join(git_dir, '.git')
    else:
        git_dir = '.'
    cmds = [
        'dpkg -s "%s" | grep Version' % package,
        'git --git-dir \'%s\' log -1' % git_dir,
    ]
    local_repo = False
    for cmd in cmds:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = p.communicate()
        if p.returncode == 0:
            if cmd.startswith('git'):
                local_repo = True
                # Get git repo version using last commit date and short hash
                try:
                    last_commit_unix_ts = _get_output(['git', '--git-dir', git_dir, 'log', '-1', '--pretty=%ct'])
                    last_commit_ts = datetime.datetime.fromtimestamp(int(last_commit_unix_ts)).strftime('%Y%m%d%H%M%S')
                    last_commit_shorthash = _get_output(['git', '--git-dir', git_dir, 'log', '-1', '--pretty=%h'])
                    revision = '%s-%s' % (last_commit_ts, last_commit_shorthash)
                except Exception as e:
                    logger.error('Unable to get revision: %s', e)
            else:
                revision = str(out, 'utf-8').replace('Version: ', '')
            break
    if '+' in revision:
        revision = revision[revision.index('+') + 1:]
    elif not revision:
        revision = '?'
    return version, revision, local_repo


def get_system_info(package=None, module=None, extra=None):
    # This function returns data for the sysinfo.html template
    os.environ['LANG'] = 'C'
    tplt_args = dict(info_sections=list())
    # Project version
    version, revision, local_repo = get_version(package, module)
    tplt_args['info_package'] = []
    tplt_args['info_package'].append(dict(label=_('Version'), value=version))
    tplt_args['info_package'].append(dict(label=_('Revision'), value=revision))
    dj_version = getattr(django, 'VERSION', '?')
    if isinstance(dj_version, tuple):
        dj_version = '.'.join([str(i) for i in dj_version])
    tplt_args['info_package'].append(dict(label=_('Django version'), value=dj_version))
    tplt_args['local_repo'] = local_repo
    tplt_args['version'] = version
    tplt_args['revision'] = revision
    tplt_args['info_sections'].append(dict(label=_('Software'), info=tplt_args['info_package']))
    # OS info
    tplt_args['info_os'] = []
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
    tplt_args['info_hdd'] = [dict(label='', value=_get_output(['df', '-h']))]
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
    gpu_model = _get_output('lspci | grep VGA').split(':')[-1].strip()
    tplt_args['info_gpu'].append(dict(label=_('Model'), value=gpu_model or '?'))
    gpu_temp = _get_output('nvidia-settings -q GPUCoreTemp | grep Attribute').split(':')[-1].strip(' .')
    try:
        int(gpu_temp)
        gpu_temp += ' °C'
    except ValueError:
        pass
    tplt_args['info_gpu'].append(dict(label=_('Temperature'), value=gpu_temp or '?'))
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
        tplt_args['info_memory'].append(dict(label=_('Total'), value='%.2f %s' % ((mem_dict.get('MemTotal', 0) / 1048576.), _('GB'))))
        tplt_args['info_memory'].append(dict(label=_('Free'), value='%.2f %s' % ((mem_dict.get('MemFree', 0) / 1048576.), _('GB'))))
        tplt_args['info_memory'].append(dict(label=_('Cached'), value='%.2f %s' % ((mem_dict.get('Cached', 0) / 1048576.), _('GB'))))
    except Exception as e:
        tplt_args['info_memory'].append(dict(label=_('Failed to get information'), value=e))
    tplt_args['info_sections'].append(dict(label=_('Memory'), info=tplt_args['info_memory']))
    # Network
    ifconfig = _get_output(['ifconfig', '-a']).strip()
    if ifconfig:
        tplt_args['info_network'] = []
        for value in ifconfig.split('\n\n'):
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
