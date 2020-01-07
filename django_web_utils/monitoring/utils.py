#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Daemon monitoring utilities
'''
import datetime
import logging
import os
import stat
import sys
# Django
from django.contrib import messages
from django.http import FileResponse, HttpResponseRedirect
from django.utils.http import http_date
from django.utils.translation import gettext_lazy as _
# django_web_utils
from django_web_utils import files_utils
from django_web_utils import system_utils
from django_web_utils.daemon.base import BaseDaemon

logger = logging.getLogger('djwutils.monitoring.utils')

FILE_SIZE_LIMIT = 524288000  # 500 MB


def clear_log(request, path, owner='self'):
    if os.path.exists(path):
        success, msg = system_utils.write_file_as(request, '', path, owner)
        if not success:
            return success, msg
    return True, str(_('Log file cleared.'))


def execute_daemon_command(request, daemon, command):
    if command not in ('start', 'restart', 'stop', 'clear_log'):
        return False, str(_('Invalid command.'))
    cls = daemon.get('cls')
    if cls and not issubclass(cls, BaseDaemon):
        return False, str(_('Given daemon class is not a subclass of Django web utils BaseDaemon.'))

    is_root = daemon.get('is_root')
    if command == 'clear_log':
        log_path = daemon.get('log_path')
        if not log_path and cls:
            log_path = cls.get_log_path()
        if not log_path:
            return False, str(_('No valid target for command.'))
        return clear_log(request, log_path, 'root' if is_root else 'self')
    elif not cls:
        return False, str(_('No valid target for command.'))

    path = sys.modules[cls.__module__].__file__
    if path.endswith('pyc'):
        path = path[:-1]
    if not os.path.isfile(path):
        logger.error('The daemon script cannot be found. Path: %s' % path)
        return False, str(_('The daemon script cannot be found.'))

    cmd = 'python3 %s %s' % (path, command)
    success, output = system_utils.execute_command(cmd, user='root' if is_root else 'self', request=request)
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
    is_root = daemon.get('is_root')
    # Check if daemon is launched
    need_password = False
    if pid_path:
        if system_utils.is_pid_running(pid_path, user='self', request=request):
            running = True
        elif not is_root:
            running = False
        else:
            if not request.session.get('pwd'):
                running = None
                need_password = True
            elif system_utils.is_pid_running(pid_path, user='root', request=request):
                running = True
            else:
                running = False
    else:
        running = None
    # Get log file properties
    size = mtime = ''
    if log_path and os.path.exists(log_path):
        size = '%s %s' % files_utils.get_unit(os.path.getsize(log_path))
        mtime = os.path.getmtime(log_path)
        mtime = datetime.datetime.fromtimestamp(mtime)
        if date_adjust_fct:
            mtime = date_adjust_fct(mtime)
        mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
    return dict(
        running=running,
        need_password=need_password,
        log_size=size,
        log_mtime=mtime,
    )


def log_view(request, path=None, tail=None, owner='user', date_adjust_fct=None):
    # Clear log
    if request.method == 'POST' and request.POST.get('submitted_form') == 'clear_log':
        success, message = clear_log(request, path, owner)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return HttpResponseRedirect(request.get_full_path())

    # Prepare display
    content = size = mtime = ''
    lines = 0
    tail_only = 'tail' in request.GET if tail is None else tail
    if os.path.exists(path):
        try:
            if 'raw' in request.GET:
                # Get raw content
                statobj = os.stat(path)
                response = FileResponse(open(path, 'rb'), content_type='text/plain')
                response['Last-Modified'] = http_date(statobj.st_mtime)
                if stat.S_ISREG(statobj.st_mode):
                    response['Content-Length'] = statobj.st_size
                return response
            fsize = os.path.getsize(path)
            size = '%s %s' % files_utils.get_unit(fsize)
            if tail_only:
                # Read only file end
                content = b''
                for segment in files_utils.reverse_read(path):
                    if segment is None:
                        break
                    content = segment + content
                    lines += segment.count(b'\n')
                    if lines > 50:
                        content = b'...%s' % content[content.index(b'\n'):]
                        break
                content = content.decode('utf-8')
            else:
                if fsize > FILE_SIZE_LIMIT:
                    content = str(_('File too large: %s.\nOnly file tail and raw file are accessible.\nWarning: getting the raw file can saturate system memory.') % size)
                else:
                    with open(path, 'r') as fd:
                        content = fd.read()
                    lines = content.count('\n')
            mtime = os.path.getmtime(path)
            mtime = datetime.datetime.fromtimestamp(mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            messages.error(request, '%s %s\n%s' % (_('Unable to display log file.'), _('Error:'), e))
    bottom_bar = lines > 20

    query_string = request.META.get('QUERY_STRING')
    if query_string and 'tail' in query_string:
        query_string = query_string.replace('&tail', '').replace('tail', '')
    return {
        'content': content,
        'size': size,
        'mtime': mtime,
        'path': path,
        'owner': owner,
        'bottom_bar': bottom_bar,
        'tail': tail_only,
        'query_string': query_string,
    }


def edit_conf_view(request, path=None, default_conf_path=None, default_conf=None, owner='user', date_adjust_fct=None):
    content = ''
    # Change configuration
    if request.method == 'POST' and request.POST.get('submitted_form') == 'change_conf':
        content = request.POST.get('conf_content')
        if content:
            if not os.path.isdir(os.path.dirname(path)):
                try:
                    os.makedirs(os.path.dirname(path))
                except Exception as e:
                    messages.error(request, '%s %s\n%s' % (_('Unable to write configuration file.'), _('Error:'), e))
                    return HttpResponseRedirect(request.get_full_path())
            success, msg = system_utils.write_file_as(request, content, path, owner)
            if not success:
                messages.error(request, '%s %s\n%s' % (_('Unable to write configuration file.'), _('Error:'), msg))
            else:
                messages.success(request, _('Configuration file updated.'))
                return HttpResponseRedirect(request.get_full_path())
        else:
            success, msg = system_utils.write_file_as(request, '', path, owner)
            if not success:
                messages.error(request, '%s %s\n%s' % (_('Unable to delete configuration file.'), _('Error:'), msg))
            else:
                messages.success(request, _('Configuration file deleted.'))
            return HttpResponseRedirect(request.get_full_path())

    # Prepare display
    size = mtime = ''
    if os.path.exists(path):
        try:
            if 'raw' in request.GET:
                # Get raw content
                statobj = os.stat(path)
                response = FileResponse(open(path, 'rb'), content_type='text/plain')
                response['Last-Modified'] = http_date(statobj.st_mtime)
                if stat.S_ISREG(statobj.st_mode):
                    response['Content-Length'] = statobj.st_size
                return response
            fsize = os.path.getsize(path)
            size = '%s %s' % files_utils.get_unit(fsize)
            if not content:
                if fsize > FILE_SIZE_LIMIT:
                    content = str(_('File too large: %s.\nOnly the raw file is accessible.\nWarning: getting the raw file can saturate system memory.') % size)
                else:
                    with open(path, 'r') as fd:
                        content = fd.read()
            mtime = os.path.getmtime(path)
            mtime = datetime.datetime.fromtimestamp(mtime)
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
    elif not default_conf and default_conf_path and os.path.isfile(default_conf_path):
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
        'owner': owner,
        'default_conf_content': default_conf_content,
        'default_conf_path': default_conf_path,
        'query_string': query_string,
    }
