#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Daemon monitoring utilities
'''
import os
import sys
import datetime
import logging
logger = logging.getLogger('djwutils.monitoring.utils')
# Django
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
# django_web_utils
from django_web_utils.daemon.base import BaseDaemon
from django_web_utils import files_utils


FILE_SIZE_LIMIT = 524288000  # 500 MB


def clear_log(path):
    if os.path.exists(path):
        try:
            with open(path, 'w+') as fd:
                fd.write('')
        except OSError, e:
            return False, unicode(_('Can not clear log file: %s') % e)
    return True, unicode(_('Log file cleared.'))


def execute_daemon_command(daemon_class, command, args=None):
    if not issubclass(daemon_class, BaseDaemon):
        return False, unicode(_('Given daemon class is not a subclass of Django web utils BaseDaemon.'))
    if command not in ('start', 'restart', 'stop', 'clear_log'):
        return False, unicode(_('Invalid command.'))
    name = daemon_class.DAEMON_NAME
    path = sys.modules[daemon_class.__module__].__file__
    if path.endswith('pyc'):
        path = path[:-1]
    if not os.path.isfile(path):
        logger.error('The daemon script cannot be found. Path: %s' % path)
        return False, unicode(_('The daemon script cannot be found.'))

    if command == 'clear_log':
        log_path = os.path.join(daemon_class.LOG_DIR, '%s.log' % name)
        return clear_log(log_path)

    try:
        cmd = 'python %s %s' % (path, command)
        if args:
            for a in args:
                cmd += ' %s' % a
        result = os.system(cmd)
        msg = ''
    except Exception, e:
        result = -1
        msg = unicode(e)
    if result != 0:
        return False, msg
    else:
        return True, msg


def daemons_statuses(daemons, date_adjust_fct=None):
    # daemons is a dict containing a dict for each daemon with the following fields:
    # [daemon_class], [pid_path], [log_path]
    data = dict()
    for name, daemon in daemons.iteritems():
        # Check if daemon is launched
        pid_path = daemon.get('pid_path')
        if not pid_path and daemon.get('daemon_class'):
            pid_path = os.path.join(daemon['daemon_class'].PID_DIR, '%s.pid' % name)
        pid = None
        if pid_path and os.path.exists(pid_path):
            try:
                with open(pid_path, 'r') as fd:
                    pid = fd.read()
            except Exception:
                pass
        running = pid and os.system('ps -p %s > /dev/null' % pid) == 0
        # Get log file properties
        log_path = daemon.get('log_path')
        if not log_path and daemon.get('daemon_class'):
            log_path = os.path.join(daemon['daemon_class'].LOG_DIR, '%s.log' % name)
        size = mtime = ''
        if log_path and os.path.exists(log_path):
            size = u'%s %s' % files_utils.get_unit(os.path.getsize(log_path))
            mtime = os.path.getmtime(log_path)
            mtime = datetime.datetime.fromtimestamp(mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
        data[name] = dict(
            running=running,
            log_size=size,
            log_mtime=mtime,
        )
    return data


def log_view(request, daemon=None, path=None, tail=None, date_adjust_fct=None):
    if daemon:
        if not issubclass(daemon, BaseDaemon):
            raise Exception('The given daemon is not a subclass of BaseDaemon.')
        path = daemon.get_log_path()

    # Clear log
    if request.method == 'POST' and request.POST.get('submitted_form') == 'clear_log':
        success, message = clear_log(path)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return HttpResponseRedirect(request.path)

    # Prepare display
    content = size = mtime = ''
    lines = 0
    tail_only = 'tail' in request.GET if tail is None else tail
    if os.path.exists(path):
        try:
            if 'raw' in request.GET:
                # Get raw content
                with open(path, 'r') as fd:
                    return HttpResponse(fd, content_type='text/plain')
            fsize = os.path.getsize(path)
            size = u'%s %s' % files_utils.get_unit(fsize)
            if tail_only:
                # Read only file end
                for segment in files_utils.reverse_read(path):
                    if segment is None:
                        break
                    content = segment + content
                    lines += segment.count('\n')
                    if lines > 50:
                        content = '...%s' % content[content.index('\n'):]
                        break
            else:
                if fsize > FILE_SIZE_LIMIT:
                    content = unicode(_('File too large: %s.\nOnly tail and raw functions are available.\nWarning: getting the raw file can saturate system memory.') % size)
                else:
                    with open(path, 'r') as fd:
                        content = fd.read()
                    lines = content.count('\n')
            mtime = os.path.getmtime(path)
            mtime = datetime.datetime.fromtimestamp(mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception, e:
            messages.error(request, u'%s %s\n%s' % (_('Unable to display log file.'), _('Error:'), e))
    bottom_bar = lines > 20
    
    return {
        'content': content,
        'size': size,
        'mtime': mtime,
        'bottom_bar': bottom_bar,
        'tail': tail_only,
    }


def edit_conf_view(request, daemon=None, path=None, default_conf_path=None, default_conf=None, date_adjust_fct=None):
    if daemon:
        if not issubclass(daemon, BaseDaemon):
            raise Exception('The given daemon is not a subclass of BaseDaemon.')
        default_conf = daemon.DEFAULTS
        if 'LOGGING_LEVEL' not in default_conf:
            default_conf['LOGGING_LEVEL'] = 'INFO'
        path = daemon.get_conf_path()

    content = ''
    # Change configuration
    if request.method == 'POST' and request.POST.get('submitted_form') == 'change_conf':
        content = request.POST.get('conf_content')
        if content:
            try:
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                with open(path, 'w+') as fd:
                    fd.write(content.encode('utf-8'))
            except Exception, e:
                messages.error(request, u'%s %s\n%s' % (_('Unable to write configuration file.'), _('Error:'), e))
            else:
                messages.success(request, _('Configuration file updated.'))
                return HttpResponseRedirect(request.path)
        else:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception, e:
                messages.error(request, u'%s %s\n%s' % (_('Unable to delete configuration file.'), _('Error:'), e))
            else:
                messages.success(request, _('Configuration file deleted.'))
            return HttpResponseRedirect(request.path)
    
    # Prepare display
    size = mtime = ''
    if os.path.exists(path):
        try:
            if 'raw' in request.GET:
                # Get raw content
                with open(path, 'r') as fd:
                    return HttpResponse(fd, content_type='text/plain')
            fsize = os.path.getsize(path)
            size = u'%s %s' % files_utils.get_unit(fsize)
            if fsize > FILE_SIZE_LIMIT:
                content = unicode(_('File too large: %s.\nOnly function is available.\nWarning: getting the raw file can saturate system memory.') % size)
            else:
                with open(path, 'r') as fd:
                    content = fd.read()
            mtime = os.path.getmtime(path)
            mtime = datetime.datetime.fromtimestamp(mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = mtime.strftime('%Y-%m-%d %H:%M:%S')
        except Exception, e:
            messages.error(request, u'%s %s\n%s' % (_('Unable to display configuration file.'), _('Error:'), e))
    # Get default conf
    default_conf_content = u''
    if isinstance(default_conf, dict):
        keys = default_conf.keys()
        keys.sort()
        for key in keys:
            if key.startswith('__'):
                continue
            val = default_conf[key]
            if isinstance(val, str):
                val = u'\'%s\'' % val
            elif isinstance(val, unicode):
                val = u'u\'%s\'' % val
            default_conf_content += u'%s = %s\n' % (key, val)
    elif not default_conf and default_conf_path and os.path.isfile(default_conf_path):
        try:
            with open(default_conf_path, 'r') as fd:
                default_conf_content = fd.read()
        except Exception, e:
            messages.error(request, u'%s %s\n%s' % (_('Unable to read default configuration file.'), _('Error:'), e))
    
    return {
        'content': content,
        'size': size,
        'mtime': mtime,
        'path': path,
        'default_conf_content': default_conf_content,
        'default_conf_path': default_conf_path,
    }
