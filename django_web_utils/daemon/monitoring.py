#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Daemon monitoring utilities
To get status of daemons.
'''
import os
import sys
import datetime
import logging
logger = logging.getLogger('djwutils.daemon.monitoring')
# Django
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext, defaultfilters
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
# django_web_utils
from django_web_utils.daemon.base import BaseDaemon
from django_web_utils.files_utils import get_unit


def clear_log(path):
    if not os.path.exists(path):
        return True, unicode(_('Log file cleared.'))
    try:
        with open(path, 'w+') as fd:
            fd.write('')
        return True, unicode(_('Log file cleared.'))
    except OSError, e:
        return False, unicode(_('Can not clear log file: %s') % e)


def execute_daemon_command(daemon_class, command, args=None):
    if not issubclass(daemon_class, BaseDaemon):
        return False, unicode(_('Given daemon class is not a subclass of Django web utils BaseDaemon.'))
    if command not in daemon_class.ALLOWED_COMMANDS:
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
    
    error = ''
    try:
        cmd = 'python %s %s' % (path, command)
        if args:
            for a in args:
                cmd += ' %s' % a
        result = os.system(cmd)
    except Exception, e:
        result = -1
        error = unicode(e)
    
    if result != 0:
        return False, error
    else:
        return True, ''


def daemons_statuses(daemons, date_adjust_fct=None):
    # daemons is a dict containing a dict for each daemon with the following fields:
    # [daemon_class], [pid_path], [log_path]
    data = dict()
    for name, daemon in daemons.iteritems():
        # check if daemon is launched
        pid_path = daemon.get('pid_path')
        if not pid_path and daemon.get('daemon_class'):
            pid_path = os.path.join(daemon['daemon_class'].PID_DIR, '%s.pid' % name)
        running = None
        if pid_path and os.path.exists(pid_path):
            try:
                pidfile = open(pid_path, 'r')
                pid = pidfile.read()
                pidfile.close()
            except Exception:
                pid = None
            running = pid and os.system('ps -p %s > /dev/null' % pid) == 0
        
        # get log file properties
        log_path = daemon.get('log_path')
        if not log_path and daemon.get('daemon_class'):
            log_path = os.path.join(daemon['daemon_class'].LOG_DIR, '%s.log' % name)
        size = 0
        unit = ''
        mtime = ''
        if log_path and os.path.exists(log_path):
            size, unit = get_unit(os.path.getsize(log_path))
            mtime = os.path.getmtime(log_path)
            mtime = datetime.datetime.fromtimestamp(mtime)
            if date_adjust_fct:
                mtime = date_adjust_fct(mtime)
            mtime = defaultfilters.date(mtime, _('l, F jS, Y, H:i'))
        data[name] = dict(
            running=running,
            log_size=size,
            log_unit=unicode(unit),
            log_mtime=mtime,
        )
    return data


def log_view(request, template, url, path, tail=False, date_adjust_fct=None, **kwargs):
    # clear log
    #***************************************************************************
    if request.method == 'POST' and request.POST.get('submitted_form') == 'clear_log':
        success, message = clear_log(path)
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        return HttpResponseRedirect(url)
    
    # prepare rendering
    #***************************************************************************
    content = ''
    size = ''
    unit = ''
    mtime = ''
    lines = 0
    if os.path.exists(path):
        f = open(path, 'r')
        content = f.read()
        f.close()
        lines = content.count('\n')
        if tail and lines > 50:
            content = '...\n%s' % ('\n'.join(content.split('\n')[-50:]))
        size, unit = get_unit(os.path.getsize(path))
        mtime = os.path.getmtime(path)
        mtime = datetime.datetime.fromtimestamp(mtime)
        if date_adjust_fct:
            mtime = date_adjust_fct(mtime)
        mtime = defaultfilters.date(mtime, _('l, F jS, Y, H:i'))
    bottom_bar = lines > 20
    
    tplt_args = {
        'content': content,
        'url': url,
        'size': size,
        'unit': unicode(unit),
        'mtime': mtime,
        'bottom_bar': bottom_bar,
        'tail': tail,
    }
    if kwargs:
        tplt_args.update(kwargs)
    return render_to_response(template, tplt_args, context_instance=RequestContext(request))


def edit_conf_view(request, template, url, path, default_conf_path=None, defaults=None, date_adjust_fct=None, **kwargs):
    content = ''
    # save modifications
    #***************************************************************************
    if request.method == 'POST' and request.POST.get('submitted_form') == 'change_conf':
        content = request.POST.get('conf_content')
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except OSError, e:
                messages.error(request, u'%s\n%s' % (_('Unable to create folder for configuration file. Error is:'), e))
        if content:
            try:
                f = open(path, 'w+')
            except Exception, e:
                messages.error(request, u'%s\n%s' % (_('Unable to write configuration file. Error is:'), e))
            else:
                f.write(content.encode('utf-8'))
                f.close()
                messages.success(request, _('Configuration file updated.'))
                return HttpResponseRedirect(url)
        else:
            try:
                os.remove(path)
            except Exception:
                pass
            messages.success(request, _('Configuration file cleared.'))
            return HttpResponseRedirect(url)
    
    # prepare rendering
    #***************************************************************************
    size = ''
    unit = ''
    mtime = ''
    if os.path.exists(path):
        if not content:
            f = open(path, 'r')
            content = f.read()
            f.close()
        size, unit = get_unit(os.path.getsize(path))
        mtime = os.path.getmtime(path)
        mtime = datetime.datetime.fromtimestamp(mtime)
        if date_adjust_fct:
            mtime = date_adjust_fct(mtime)
        mtime = defaultfilters.date(mtime, _('l, F jS, Y, H:i'))
    # get default confdefault_conf_module
    default_conf = u''
    if default_conf_path and os.path.isfile(default_conf_path):
        f = open(default_conf_path, 'r')
        default_conf = f.read()
        f.close()
    elif defaults:
        keys = defaults.keys()
        keys.sort()
        for key in keys:
            if key.startswith('__'):
                continue
            val = defaults[key]
            if isinstance(val, str):
                val = u'\'%s\'' % val
            elif isinstance(val, unicode):
                val = u'u\'%s\'' % val
            default_conf += u'%s = %s\n' % (key, val)
    
    tplt_args = {
        'content': content,
        'url': url,
        'size': size,
        'unit': unicode(unit),
        'mtime': mtime,
        'path': path,
        'default_conf': default_conf,
        'default_conf_path': default_conf_path,
    }
    if kwargs:
        tplt_args.update(kwargs)
    return render_to_response(template, tplt_args, context_instance=RequestContext(request))
