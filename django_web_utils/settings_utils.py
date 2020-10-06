#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Module to handle file settings.
The OVERRIDE_PATH setting must be set to the local settings override path.
'''
import datetime
import logging
import os
# Django
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# Django web utils
from django_web_utils.module_utils import import_module_by_python_path

logger = logging.getLogger('djwutils.settings_utils')


# backup_settings function
# ----------------------------------------------------------------------------
def backup_settings():
    path = settings.OVERRIDE_PATH
    if not os.path.exists(path):
        return
    # get settings mtime
    mtime = os.path.getmtime(path)
    mtime = datetime.datetime.fromtimestamp(mtime)
    # copy settings file
    try:
        with open(path, 'rb') as fo:
            current = fo.read()
        with open('%s.backup_%s.py' % (path, mtime.strftime('%Y-%m-%d_%H-%M-%S')), 'wb') as fo:
            fo.write(current)
    except Exception as e:
        raise Exception('%s %s' % (_('Failed to backup settings:'), e))


# set_settings function
# ----------------------------------------------------------------------------
def set_settings(tuples, restart=True):
    if not tuples:
        return True, _('No changes to save.')
    content = ''
    if os.path.exists(settings.OVERRIDE_PATH):
        with open(settings.OVERRIDE_PATH, 'r') as fd:
            content = fd.read()

    for name, value in tuples:
        # change locally settings
        setattr(settings, name, value)
        # get content to write in var
        if value is None:
            value_str = 'None'
        elif value is True:
            value_str = 'True'
        elif value is False:
            value_str = 'False'
        elif isinstance(value, (int, float)):
            value_str = str(value)
        else:
            value_str = str(value)
            value_str = value_str.replace('\'', '\\\'').replace('\n', '\\n').replace('\r', '')
            value_str = '\'%s\'' % value_str

        lindex = content.find(name)
        if lindex < 0:
            # add var to settings
            content += '\n%s = %s' % (name, value_str)
        else:
            # change current var
            lindex += len(name)
            sub = content[lindex:]
            rindex = sub.find('\n')
            if rindex < 0:
                content = '%s = %s' % (content[:lindex], value_str)
            else:
                rindex += lindex
                content = '%s = %s%s' % (content[:lindex], value_str, content[rindex:])

    try:
        if content:
            # backup settings before writing
            backup_settings()
            # write settings
            with open(settings.OVERRIDE_PATH, 'w') as fd:
                fd.write(content)
    except Exception as e:
        logger.error('Unable to write configuration file. %s' % e)
        return False, '%s %s' % (_('Unable to write configuration file:'), e)
    msg = str(_('Your changes will be active after the server restart.'))
    if restart:
        success, restart_msg = restart_server()
        msg += '\n'
        if not success:
            msg += str(_('Warning:'))
        msg += str(restart_msg)
    return True, msg


# remove_settings function
# ----------------------------------------------------------------------------
def remove_settings(*names):
    # WARNING: this function supports only variables in one line
    # TODO: remove this constraint
    if os.path.exists(settings.OVERRIDE_PATH) and names:
        content = ''
        with open(settings.OVERRIDE_PATH, 'r') as fd:
            content = fd.read()

        lines = content.split('\n')
        removed_lines = 0
        new_lines = list()
        for line in lines:
            removed = False
            for name in names:
                if line.startswith(name):
                    removed_lines += 1
                    removed = True
                    break
            if not removed:
                new_lines.append(line)

        if removed_lines > 0:
            try:
                # backup settings before writing
                backup_settings()
                # write settings
                with open(settings.OVERRIDE_PATH, 'w') as fd:
                    fd.write('\n'.join(new_lines))
            except Exception as e:
                logger.error('Unable to write configuration file. %s' % e)
                return False, '%s %s' % (_('Unable to write configuration file:'), e)
    msg = str(_('Your changes will be active after the server restart.'))
    success, restart_msg = restart_server()
    msg += '\n'
    if not success:
        msg += str(_('Warning:'))
    msg += str(restart_msg)
    return True, msg


# restart_server function
# ----------------------------------------------------------------------------
def restart_server():
    '''
    This function triggers a restart of the site itself.
    When this function is called, respond to user then wait 2 sec and restart server.
    '''
    if getattr(settings, 'DEBUG', False):
        return True, _('No restart because server is in debug mode.')

    # Get restart function
    restart_fct_path = getattr(settings, 'RESTART_FUNCTION', None)
    if not restart_fct_path:
        return True, _('No restart function defined.')

    try:
        restart_fct = import_module_by_python_path(restart_fct_path)
        return restart_fct()
    except Exception as e:
        return False, '%s %s' % (_('Failed to restart server:'), e)
