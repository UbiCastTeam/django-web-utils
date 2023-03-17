"""
System information
"""
import logging
import os
import re
import subprocess
import sys
# Django
from django.utils.translation import gettext_lazy as _
import django
# django_web_utils
from django_web_utils.packages_utils import get_version

logger = logging.getLogger('djwutils.monitoring.sysinfo')


def _get_output(cmd):
    env = dict(os.environ)
    env['LANG'] = 'C.UTF-8'
    env['LC_ALL'] = 'C.UTF-8'
    try:
        p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
    except Exception as e:
        return str(e).strip()
    return p.stdout.strip()


_repo_info = None


def _get_repo_info(package, module):
    # FIXME: Cache is global and should be relative to args
    global _repo_info
    if _repo_info is None:
        _repo_info = get_version(package, module)
    return _repo_info


_soft_info = None


def _get_soft_info(package, module):
    global _soft_info
    if _soft_info is None:
        # The information are read only once
        version, revision, local_repo = _get_repo_info(package, module)
        dj_version = getattr(django, 'VERSION', '?')
        if isinstance(dj_version, tuple):
            dj_version = '.'.join([str(i) for i in dj_version])
        try:
            from django.conf import settings
            db_engine = ', '.join([db['ENGINE'] for db in settings.DATABASES.values()])
            time_zone = getattr(settings, 'TIME_ZONE', '?')
        except Exception as e:
            logger.debug('Failed to get database TIME_ZONE setting: %s', e)
            db_engine = None
            time_zone = None
        # Prepare rendering
        _soft_info = [
            {'label': _('Version'), 'value': version},
            {'label': _('Revision'), 'value': revision},
            {'label': _('Python version'), 'value': sys.version},
            {'label': _('Django version'), 'value': dj_version},
        ]
        if db_engine is not None:
            _soft_info.append({'label': _('Database engine'), 'value': db_engine})
        if time_zone is not None:
            _soft_info.append({'label': _('Django time zone'), 'value': time_zone})
    result = _soft_info.copy()
    return result


_os_info = None


def _get_os_info():
    global _os_info
    if _os_info is None:
        # The information are read only once
        os_name = _get_output(['grep', 'PRETTY_NAME', '/etc/os-release']).replace('PRETTY_NAME', '').strip('"= \t')
        # Prepare rendering
        _os_info = [
            {'label': _('Description'), 'value': os_name or '?'},
            {'label': _('Kernel'), 'value': _get_output(['uname', '-r'])},
            {'label': _('Hostname'), 'value': _get_output(['uname', '-n'])},
            {'label': _('Time zone'), 'value': _get_output(['cat', '/etc/timezone'])},
        ]
    # Add dynamic information
    result = _os_info + [
        {'label': _('Uptime'), 'value': _get_output(['uptime', '-p'])},
        {'label': _('Load'), 'value': _get_output(['cat', '/proc/loadavg'])},
    ]
    return result


_cpu_info = None


def _get_cpu_info():
    global _cpu_info
    if _cpu_info is None:
        # The information are read only once
        info = {'total cores': 0}
        try:
            with open('/proc/cpuinfo', 'r') as fo:
                for line in fo:
                    index = line.find(':')
                    if index > 0:
                        if line.startswith('processor'):
                            info['total cores'] += 1
                        else:
                            field = line[:index].strip()
                            value = line[index + 1:].strip()
                            info[field] = value
        except Exception as e:
            logger.debug('Failed to read CPU information file: %s', e)
        info['model name'] = ' '.join(info.get('model name', '').split())
        if '@' in info.get('model name', ''):
            # Try to get default frequency
            index = info['model name'].find('@')
            info['default freq'] = info['model name'][index + 1:].strip().replace('GHz', ' GHz')
            info['model name'] = info['model name'][:index].strip()
        # Prepare rendering
        _cpu_info = [
            {'label': _('Model'), 'value': info.get('model name', '?')},
            {'label': _('Cores'), 'value': info['total cores'] or '?'},
            {'label': _('Default frequency'), 'value': info.get('default freq', '?')},
        ]
    result = _cpu_info.copy()
    return result


_gpu_info = None


def _get_gpu_info():
    global _gpu_info
    if _gpu_info is None:
        # The information are read only once
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
        _gpu_info = [
            {'label': _('Model'), 'value': gpu_model or '?'},
        ]
    result = _gpu_info.copy()
    return result


def get_system_info(package=None, module=None, extra=None):
    # This function returns data for the sysinfo.html template
    tplt_args = {'info_sections': []}
    # Project version
    version, revision, local_repo = _get_repo_info(package, module)
    tplt_args['local_repo'] = local_repo
    tplt_args['version'] = version
    tplt_args['revision'] = revision
    # Software info
    tplt_args['info_package'] = _get_soft_info(package, module)
    tplt_args['info_sections'].append({'label': _('Software'), 'info': tplt_args['info_package']})
    # OS info
    tplt_args['info_os'] = _get_os_info()
    tplt_args['info_sections'].append({'label': _('OS'), 'info': tplt_args['info_os']})
    # HDD
    dfh = _get_output(['df', '-h']).strip()
    if dfh:
        tplt_args['info_hdd'] = []
        for value in dfh.split('\n'):
            tplt_args['info_hdd'].append({'label': '', 'value': value})
        tplt_args['info_sections'].append({'label': _('HDD'), 'info': tplt_args['info_hdd']})
    # CPU
    tplt_args['info_cpu'] = _get_cpu_info()
    tplt_args['info_sections'].append({'label': _('CPU'), 'info': tplt_args['info_cpu']})
    # GPU
    tplt_args['info_gpu'] = _get_gpu_info()
    tplt_args['info_sections'].append({'label': _('GPU'), 'info': tplt_args['info_gpu']})
    # Memory
    meminfo_file = _get_output(['cat', '/proc/meminfo'])
    tplt_args['info_memory'] = []
    try:
        mem_dict = {}
        for line in meminfo_file.split('\n'):
            key, value = line.rstrip(' kB').split(':')
            try:
                value = int(value.strip())
            except ValueError:
                continue
            mem_dict[key.strip()] = value
        tplt_args['info_memory'].append({'label': _('Total'), 'value': '%.2f %s' % ((mem_dict.get('MemTotal', 0) / 1000000.), _('GB'))})
        tplt_args['info_memory'].append({'label': _('Free'), 'value': '%.2f %s' % ((mem_dict.get('MemFree', 0) / 1000000.), _('GB'))})
        tplt_args['info_memory'].append({'label': _('Cached'), 'value': '%.2f %s' % ((mem_dict.get('Cached', 0) / 1000000.), _('GB'))})
    except Exception as e:
        tplt_args['info_memory'].append({'label': _('Failed to get information'), 'value': e})
    tplt_args['info_sections'].append({'label': _('Memory'), 'info': tplt_args['info_memory']})
    # Network
    ipaddr = _get_output(['ip', 'addr']).strip()
    if ipaddr:
        tplt_args['info_network'] = []
        for value in ipaddr.split('\n'):
            tplt_args['info_network'].append({'label': '', 'value': value})
        tplt_args['info_sections'].append({'label': _('Network'), 'info': tplt_args['info_network']})
    # Sensors
    sensors = _get_output(['sensors']).strip()
    if sensors:
        tplt_args['info_sensors'] = []
        for value in sensors.split('\n\n'):
            tplt_args['info_sensors'].append({'label': '', 'value': value})
        tplt_args['info_sections'].append({'label': _('Sensors'), 'info': tplt_args['info_sensors']})
    # Extra data
    if extra:
        for section, values in extra.items():
            if section in tplt_args:
                tplt_args[section].extend(values)
            else:
                tplt_args[section] = values
    return tplt_args
