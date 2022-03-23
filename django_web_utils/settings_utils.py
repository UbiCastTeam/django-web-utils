#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Module to handle file settings.
The OVERRIDE_PATH setting must be set to the local settings override path.
'''
import datetime
import logging
import os
import sys
from typing import Iterable
# Django
from django.conf import settings, ENVIRONMENT_VARIABLE
from django.utils.functional import empty
from django.utils.translation import gettext as _

logger = logging.getLogger('djwutils.settings_utils')


# backup_settings function
# ----------------------------------------------------------------------------
def backup_settings():
    override_path = getattr(settings, 'OVERRIDE_PATH', None)
    if not override_path or not os.path.exists(override_path):
        return
    # get settings mtime
    mtime = os.path.getmtime(override_path)
    mtime = datetime.datetime.fromtimestamp(mtime)
    # copy settings file
    try:
        with open(override_path, 'rb') as fo:
            current = fo.read()
        with open('%s.backup_%s.py' % (override_path, mtime.strftime('%Y-%m-%d_%H-%M-%S')), 'wb') as fo:
            fo.write(current)
    except Exception as e:
        raise Exception('%s %s' % (_('Failed to backup settings:'), e))


def _get_value_str(value):
    if value is None:
        value_str = 'None'
    elif value is True:
        value_str = 'True'
    elif value is False:
        value_str = 'False'
    elif isinstance(value, (int, float)):
        value_str = str(value)
    elif isinstance(value, list):
        value_str = '['
        for sub_val in value:
            value_str += _get_value_str(sub_val) + ', '
        value_str += ']'
    elif isinstance(value, tuple):
        value_str = '('
        for sub_val in value:
            value_str += _get_value_str(sub_val) + ', '
        value_str += ')'
    elif isinstance(value, dict):
        value_str = '{'
        for key, sub_val in value.items():
            value_str += '\'' + str(key) + '\': ' + _get_value_str(sub_val) + ', '
        value_str += '}'
    else:
        value_str = str(value)
        value_str = value_str.replace('\'', '\\\'').replace('\n', '\\n').replace('\r', '')
        value_str = '\'%s\'' % value_str
    return value_str


# set_settings function
# ----------------------------------------------------------------------------
def set_settings(tuples, restart=True):
    if not tuples:
        return True, _('No changes to save.')

    override_path = getattr(settings, 'OVERRIDE_PATH', None)
    if not override_path:
        # Test mode usual use case
        for name, value in tuples:
            # change locally settings
            setattr(settings, name, value)
            logger.info('Unable to write configuration file, no value is set for "OVERRIDE_PATH" in settings. Ignore this message if running tests.')
        msg = _('Your changes were not saved but were applied to the running software.')
    else:
        content = ''
        if os.path.exists(override_path):
            with open(override_path, 'r') as fd:
                content = fd.read()

        for name, value in tuples:
            # change locally settings
            setattr(settings, name, value)
            # get content to write in var
            value_str = _get_value_str(value)

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
                with open(override_path, 'w') as fd:
                    fd.write(content)
        except Exception as e:
            logger.error('Unable to write configuration file. %s', e)
            return False, '%s %s' % (_('Unable to write configuration file:'), e)
        msg = _('Your changes will be active after the service restart.')
        if restart:
            msg += '\n' + _('The service will be restarted in 2 seconds.')
            # the service restart should be handled with the "touch-reload" uwsgi
            # parameter (should be set with the settings override path).
    return True, msg


# remove_settings function
# ----------------------------------------------------------------------------
def remove_settings(*names, restart=True):
    # WARNING: this function supports only variables in one line
    # TODO: remove this constraint

    # Change locally settings
    for name in names:
        delattr(settings, name)

    override_path = getattr(settings, 'OVERRIDE_PATH', None)
    if not override_path:
        # Test mode usual use case
        logger.info('Unable to write configuration file, no value is set for "OVERRIDE_PATH" in settings. Ignore this message if running tests.')
        msg = _('Your changes were not saved but were applied to the running software.')
    else:
        if os.path.exists(override_path) and names:
            content = ''
            with open(override_path, 'r') as fd:
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
                    with open(override_path, 'w') as fd:
                        fd.write('\n'.join(new_lines))
                except Exception as e:
                    logger.error('Unable to write configuration file. %s' % e)
                    return False, '%s %s' % (_('Unable to write configuration file:'), e)
        msg = _('Your changes will be active after the service restart.')
        if restart:
            msg += '\n' + _('The service will be restarted in 2 seconds.')
            # the service restart should be handled with the "touch-reload" uwsgi
            # parameter (should be set with the settings override path).
    return True, msg


# reload_settings function
# ----------------------------------------------------------------------------
def reload_settings(modules: Iterable[str] = ()):
    """
    Reload django's settings by forcing the module it depends on
    (DJANGO_SETTINGS_MODULE) to be re-imported. The global django settings
    instance (`from django.conf import settings`) will be refreshed in place
    (i.e. any change in the settings will be visible globally).

    ! NOT THREAD-SAFE !

    :param modules: any other module paths that need to be re-imported.
    """
    from django.conf import settings, ENVIRONMENT_VARIABLE
    for module_path in (*modules, os.environ.get(ENVIRONMENT_VARIABLE)):
        sys.modules.pop(module_path)

    settings._wrapped = empty
