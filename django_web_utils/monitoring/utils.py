import datetime
import gzip
import logging
import re
import stat
import subprocess
import sys
from pathlib import Path

from django.contrib import messages
from django.http import FileResponse
from django.utils.http import http_date
from django.utils.translation import gettext as _

from django_web_utils import files_utils
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
        logger.warning('The daemon script cannot be found. Path: %s', path)
        return False, _('The daemon script cannot be found.')

    p = subprocess.run(
        ['python3', str(path), command], encoding='utf-8',
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    success = p.returncode == 0
    output = p.stdout.strip()
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
    try:
        pid_value = int(Path(pid_path).read_text())
    except (FileNotFoundError, ValueError, TypeError):
        pid_value = 0
    if pid_value > 0:
        p = subprocess.run(
            ['ps', '-p', str(pid_value)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        running = p.returncode == 0
    else:
        running = False
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
