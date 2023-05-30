"""
Module to handle file settings.
The OVERRIDE_PATH setting must be set to the local settings override path.
"""
import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Any

from django.conf import settings, ENVIRONMENT_VARIABLE
from django.utils.functional import empty
from django.utils.translation import gettext as _

logger = logging.getLogger('djwutils.settings_utils')


def backup_settings(max_backups: int = 10) -> Optional[Path]:
    """
    Make a copy of the settings override file.
    Only one backup is made per day and at maximum 10 backups (default).
    """
    override_path = Path(settings.OVERRIDE_PATH) if getattr(settings, 'OVERRIDE_PATH', None) else None
    if not override_path or not override_path.exists():
        return

    mtime = override_path.stat().st_mtime
    date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

    backup_path = override_path.parent / f'{override_path.name}.backup_{date_str}.py'
    if backup_path.exists():
        return backup_path

    paths = sorted([
        path
        for path in override_path.parent.iterdir()
        if path.is_file() and path.name.startswith(f'{override_path.name}.backup_')
    ])
    while len(paths) >= max_backups:
        paths.pop(0).unlink()

    current = override_path.read_bytes()
    backup_path.write_bytes(current)
    return backup_path


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
            value_str += _get_value_str(key) + ': ' + _get_value_str(sub_val) + ', '
        value_str += '}'
    else:
        value_str = str(value)
        value_str = value_str.replace('\'', '\\\'').replace('\n', '\\n').replace('\r', '')
        value_str = '\'%s\'' % value_str
    return value_str


def set_settings(**data: Any) -> tuple[bool, str]:
    # WARNING: this function supports only variables in one line

    if not data:
        return True, _('No changes to save.')

    # Change locally settings
    for key, value in data.items():
        setattr(settings, key, value)
    logger.info('Updating following settings: %s', list(data.keys()))

    override_path = Path(settings.OVERRIDE_PATH) if getattr(settings, 'OVERRIDE_PATH', None) else None
    if not override_path:
        # Test mode usual use case
        logger.info(
            'Unable to write configuration file, no value is set for "OVERRIDE_PATH" in settings. '
            'Ignore this message if running tests.')
        msg = _('Your changes were not saved but were applied to the running software.')
        return True, msg

    # Update settings file
    try:
        content = override_path.read_text().strip() + '\n'
    except FileNotFoundError:
        content = ''

    for key, value in data.items():
        # Get content to write in var
        value_str = _get_value_str(value)

        lindex = content.find(key)
        if lindex < 0:
            # Add var to settings
            content += '%s = %s\n' % (key, value_str)
        else:
            # Change current var
            lindex += len(key)
            sub = content[lindex:]
            rindex = sub.find('\n')
            if rindex < 0:
                content = '%s = %s' % (content[:lindex], value_str)
            else:
                rindex += lindex
                content = '%s = %s%s' % (content[:lindex], value_str, content[rindex:])
    content = content.strip() + '\n'

    try:
        if content:
            # Backup settings before writing
            backup_settings()
            # Write settings
            override_path.write_text(content)
    except OSError as e:
        logger.error('Unable to write configuration file. %s', e)
        return False, '%s %s' % (_('Unable to write configuration file:'), e)

    msg = _('Your changes have been applied. The service will be reloaded in a few seconds to make them effective.')
    # The service reload should be handled with the "touch-reload" uwsgi
    # parameter (should be set with the settings override path).
    return True, msg


def remove_settings(*keys: str) -> tuple[bool, str]:
    # WARNING: this function supports only variables in one line

    if not keys:
        return True, _('No changes to save.')
    logger.info('Removing following settings: %s', keys)

    # Change locally settings
    for key in keys:
        if hasattr(settings, key):
            delattr(settings, key)

    override_path = Path(settings.OVERRIDE_PATH) if getattr(settings, 'OVERRIDE_PATH', None) else None
    if not override_path:
        # Test mode usual use case
        logger.info(
            'Unable to write configuration file, no value is set for "OVERRIDE_PATH" in settings. '
            'Ignore this message if running tests.')
        msg = _('Your changes were not saved but were applied to the running software.')
        return True, msg

    # Update settings file
    if override_path.exists() and keys:
        content = override_path.read_text().strip() + '\n'

        removed_lines = 0
        new_lines = []
        for line in content.split('\n'):
            key = line.split('=', 1)[0].strip()
            if key in keys:
                removed_lines += 1
            else:
                new_lines.append(line)

        if removed_lines > 0:
            content = '\n'.join(new_lines)
            try:
                # Backup settings before writing
                backup_settings()
                # Write settings
                override_path.write_text(content)
            except OSError as e:
                logger.error('Unable to write configuration file. %s' % e)
                return False, '%s %s' % (_('Unable to write configuration file:'), e)

    msg = _('Your changes have been applied. The service will be reloaded in a few seconds to make them effective.')
    # The service reload should be handled with the "touch-reload" uwsgi
    # parameter (should be set with the settings override path).
    return True, msg


def reload_settings(modules: Iterable[str] = ()) -> None:
    """
    Reload django's settings by forcing the module it depends on
    (DJANGO_SETTINGS_MODULE) to be re-imported. The global django settings
    instance (`from django.conf import settings`) will be refreshed in place
    (i.e. any change in the settings will be visible globally).

    ! NOT THREAD-SAFE !

    :param modules: any other module paths that need to be re-imported.
    """
    for module_path in (*modules, os.environ.get(ENVIRONMENT_VARIABLE)):
        sys.modules.pop(module_path)

    settings._wrapped = empty
