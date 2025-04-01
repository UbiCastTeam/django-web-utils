import datetime
import gzip
import logging
import re
import stat
import sys
from pathlib import Path

from django.contrib import messages
from django.http import FileResponse, HttpResponseRedirect
from django.utils.http import http_date
from django.utils.translation import gettext as _

from django_web_utils import files_utils
from django_web_utils import system_utils
from django_web_utils.daemon.base import BaseDaemon

logger = logging.getLogger('djwutils.monitoring.utils')

FILE_SIZE_LIMIT = 524_288_000  # 500 MiB
FILE_SIZE_LIMIT_GZ = 104_857_600  # 100 MiB


def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    '''
    return [
        (int(val) if val.isdigit() else val)
        for val in re.split(r'(\d+)', text)
    ]


def execute_daemon_command(request, daemon, command):
    if command not in ('start', 'restart', 'stop'):
        return False, _('Invalid command.')
    cls = daemon.get('cls')
    if not cls:
        return False, _('No valid target for command.')
    if cls and not issubclass(cls, BaseDaemon):
        return False, _('Given daemon class is not a subclass of Django web utils BaseDaemon.')

    path = sys.modules[cls.__module__].__file__
    if path.endswith('pyc'):
        path = path[:-1]
    path = Path(path)
    if not path.is_file():
        logger.error('The daemon script cannot be found. Path: %s', path)
        return False, _('The daemon script cannot be found.')

    cmd = f'python3 "{path}" {command}'
    success, output = system_utils.execute_command(cmd, user='self', request=request)
    if not output:
        output = 'No output from command.'
    return success, output


def get_daemon_status(request, daemon, date_adjust_fct=None):
    if daemon.get('cls'):
        pid_path = daemon['cls'].get_pid_path()
        log_path = daemon['cls'].get_log_path()
    else:
        pid_path = daemon.get('pid_path')
        log_path = daemon.get('log_path')
    if not log_path and daemon.get('only_conf'):
        log_path = daemon.get('conf_path')
    # Check if daemon is launched
    if pid_path:
        running = system_utils.is_pid_running(pid_path, user='self', request=request)
    else:
        running = None
    # Get log file properties
    size = mtime = ''
    if log_path and log_path.exists():
        statobj = log_path.stat()
        size = files_utils.get_size_display(statobj.st_size)
        mtime = datetime.datetime.fromtimestamp(statobj.st_mtime)
        if date_adjust_fct:
            mtime = date_adjust_fct(mtime)
        mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
    return dict(
        running=running,
        log_size=size,
        log_mtime=mtime,
    )


def log_view(request, path, tail=None, rotated_access=False, date_adjust_fct=None):
    # Prepare display
    content = size = mtime = ''
    lines = 0
    tail_only = 'tail' in request.GET if tail is None else tail
    name = path.name
    paths = {'': path}
    if rotated_access:
        paths.update({
            p.name.removeprefix(name): p
            for p in path.parent.glob(f'{name}*')
            if p.name != name
        })
    suffix = request.GET.get('suffix', '') if rotated_access else ''
    if suffix and suffix not in paths:
        messages.error(request, _('The requested suffix does not exist.'))
        suffix = ''
    picked_path = paths[suffix] if suffix else path
    is_gz = picked_path.name.endswith('.gz')
    if picked_path.exists():
        try:
            statobj = picked_path.stat()
            if 'raw' in request.GET:
                # Get raw content
                ctype = 'text/plain+gzip' if is_gz else 'text/plain'
                response = FileResponse(open(picked_path, 'rb'), content_type=f'{ctype}; charset=utf-8')
                response['Last-Modified'] = http_date(statobj.st_mtime)
                if stat.S_ISREG(statobj.st_mode):
                    response['Content-Length'] = statobj.st_size
                if is_gz:
                    response['Content-Encoding'] = 'gzip'
                return response
            size = files_utils.get_size_display(statobj.st_size)
            mtime = datetime.datetime.fromtimestamp(statobj.st_mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
            if tail_only:
                # Read only file end
                if is_gz:
                    content = _('Partial read of gzip files is not supported. Please get the complete file to read its content.')
                else:
                    content = b''
                    for segment in files_utils.reverse_read(picked_path):
                        if segment is None:
                            break
                        content = segment + content
                        lines += segment.count(b'\n')
                        if lines > 250:
                            content = b'...%s' % content[content.index(b'\n'):]
                            break
                    content = content.decode('utf-8')
            elif (
                (not is_gz and statobj.st_size > FILE_SIZE_LIMIT)
                or (is_gz and statobj.st_size > FILE_SIZE_LIMIT_GZ)
            ):
                content = _('File too large: %s.\nOnly file tail and raw file are accessible.\nWarning: getting the raw file can saturate system memory.') % size
            else:
                content = picked_path.read_bytes()
                if is_gz:
                    content = gzip.decompress(content)
                content = content.decode('utf-8')
                lines = content.count('\n')
        except Exception as e:
            messages.error(request, '%s %s\n%s' % (_('Unable to display log file.'), _('Error:'), e))
    bottom_bar = lines > 20

    return {
        'file_content': content,
        'file_size': size,
        'file_mtime': mtime,
        'file_name': name,
        'file_is_gz': is_gz,
        'suffix': suffix,
        'suffixes': sorted(paths.keys(), key=natural_keys),
        'bottom_bar': bottom_bar,
        'tail': tail_only,
    }


def edit_conf_view(request, path=None, default_conf_path=None, default_conf=None, date_adjust_fct=None):
    content = ''
    # Change configuration
    if request.method == 'POST' and request.POST.get('submitted_form') == 'change_conf':
        if not path:
            messages.error(request, _('This daemon has no configuration file.'))
        else:
            content = request.POST.get('conf_content')
            if content:
                try:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content)
                except OSError as err:
                    messages.error(request, '%s %s\n%s' % (_('Unable to write configuration file.'), _('Error:'), err))
                    return HttpResponseRedirect(request.get_full_path())
                messages.success(request, _('Configuration file updated.'))
                return HttpResponseRedirect(request.get_full_path())
            else:
                if path.exists():
                    try:
                        path.write_bytes(b'')
                    except OSError as err:
                        messages.error(request, '%s %s\n%s' % (_('Unable to write configuration file.'), _('Error:'), err))
                        return HttpResponseRedirect(request.get_full_path())
                messages.success(request, _('Configuration file cleared.'))
                return HttpResponseRedirect(request.get_full_path())

    # Prepare display
    size = mtime = ''
    if path.exists():
        try:
            statobj = path.stat()
            if 'raw' in request.GET:
                # Get raw content
                response = FileResponse(open(path, 'rb'), content_type='text/plain; charset=utf-8')
                response['Last-Modified'] = http_date(statobj.st_mtime)
                if stat.S_ISREG(statobj.st_mode):
                    response['Content-Length'] = statobj.st_size
                return response
            size = files_utils.get_size_display(statobj.st_size)
            if not content:
                if statobj.st_size > FILE_SIZE_LIMIT:
                    content = _('File too large: %s.\nOnly the raw file is accessible.\nWarning: getting the raw file can saturate system memory.') % size
                else:
                    content = path.read_text()
            mtime = datetime.datetime.fromtimestamp(statobj.st_mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            messages.error(request, '%s %s\n%s' % (_('Unable to display configuration file.'), _('Error:'), e))
    # Get default conf
    default_conf_content = ''
    if isinstance(default_conf, dict):
        keys = list(default_conf.keys())
        keys.sort()
        for key in keys:
            if key.startswith('__'):
                continue
            val = default_conf[key]
            if isinstance(val, str):
                val = '\'%s\'' % val
            elif isinstance(val, str):
                val = 'u\'%s\'' % val
            default_conf_content += '%s = %s\n' % (key, val)
    elif not default_conf and default_conf_path and Path(default_conf_path).is_file():
        try:
            with open(default_conf_path, 'r') as fd:
                default_conf_content = fd.read()
        except Exception as e:
            messages.error(request, '%s %s\n%s' % (_('Unable to read default configuration file.'), _('Error:'), e))

    query_string = request.META.get('QUERY_STRING')
    if query_string and 'tail' in query_string:
        query_string = query_string.replace('&tail', '').replace('tail', '')
    return {
        'content': content,
        'size': size,
        'mtime': mtime,
        'path': path,
        'default_conf_content': default_conf_content,
        'default_conf_path': default_conf_path,
        'query_string': query_string,
    }
