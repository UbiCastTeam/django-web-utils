"""
Module to handle file settings in TOML format or Python format.
The OVERRIDE_PATH setting must be set to the local settings override path.
This module handles only settings with ASCII name.
"""
import datetime
import logging
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Optional, Any

from django.conf import settings, ENVIRONMENT_VARIABLE
from django.utils.functional import empty
from django.utils.translation import gettext as _

from django_web_utils.files_utils import backup_file

logger = logging.getLogger('djwutils.settings_utils')

# Special value to mark settings fields that should be reseted to default in "set_settings"
TO_RESET = object()


def backup_settings() -> Optional[Path]:
    """
    Make a backup copy of the settings override file.
    See `backup_file` description for more information.
    """
    if getattr(settings, 'OVERRIDE_PATH', None):
        return backup_file(Path(settings.OVERRIDE_PATH))


def _get_toml_value_str(value):
    if value is None:
        raise ValueError('The toml format does not support None.')
    elif value is True:
        value_str = 'true'
    elif value is False:
        value_str = 'false'
    elif isinstance(value, (int, float)):
        value_str = str(value)
    elif isinstance(value, datetime.date):
        value_str = value.strftime('%Y-%m-%d')
    elif isinstance(value, datetime.datetime):
        value_str = value.strftime('%Y-%m-%dT%H:%M:%S')
    elif isinstance(value, (list, tuple)):
        value_str = '['
        for sub_val in value:
            value_str += _get_toml_value_str(sub_val) + ', '
        value_str = value_str.rstrip(', ')
        value_str += ']'
    elif isinstance(value, dict):
        value_str = '{'
        for key, sub_val in value.items():
            value_str += _get_toml_value_str(key) + ': ' + _get_toml_value_str(sub_val) + ', '
        value_str = value_str.rstrip(', ')
        value_str += '}'
    else:
        # The `repr` function is used to escape all special characters like `\`
        value_str = '"' + repr(str(value).replace('\r', ''))[1:-1].replace("\\'", "'").replace('"', '\\"') + '"'
    return value_str


def _get_py_value_str(value):
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
            value_str += _get_py_value_str(sub_val) + ', '
        value_str = value_str.rstrip(', ')
        value_str += ']'
    elif isinstance(value, tuple):
        value_str = '('
        for sub_val in value:
            value_str += _get_py_value_str(sub_val) + ', '
        value_str = value_str.rstrip(', ')
        value_str += ')'
    elif isinstance(value, dict):
        value_str = '{'
        for key, sub_val in value.items():
            value_str += _get_py_value_str(key) + ': ' + _get_py_value_str(sub_val) + ', '
        value_str = value_str.rstrip(', ')
        value_str += '}'
    else:
        # The `repr` function is used to escape all special characters like `\`
        value_str = repr(str(value).replace('\r', ''))
    return value_str


def set_settings(**data: Any) -> tuple[bool, str]:
    # WARNING: this function supports only variables in one line

    if not data:
        return True, _('No changes to save.')

    # Change locally settings
    for key, value in data.items():
        if not re.match(r'[A-Za-z][A-Za-z0-9_]*', key):
            return False, (_('Invalid setting name: %s') % key)
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

    # Get content
    try:
        initial_content = override_path.read_text()
    except FileNotFoundError:
        initial_content = ''
    content = initial_content.strip()
    if content and not content.endswith('\n'):
        content += '\n'

    if override_path.suffix == '.toml':
        str_fct = _get_toml_value_str
    else:
        str_fct = _get_py_value_str

    # Update content
    for key, value in data.items():
        if value is TO_RESET:
            # Remove value from settings
            content = re.sub(fr'(^|\n)\s*{key}\s*=.+(\n|$)', r'\1', content)
        else:
            value_str = str_fct(value)
            # Do not use `re.sub` here because it breaks escaping of `\`:
            # https://docs.python.org/3/library/re.html#re.sub
            match = re.search(fr'(^|\n)(\s*){key}\s*=.+($|\n)', content)
            if match:
                start, end = match.span()
                grps = match.groups()
                content = f'{content[:start]}{grps[0]}{grps[1]}{key} = {value_str}{grps[2]}{content[end:]}'
            else:
                content += f'{key} = {value_str}\n'

    # Write changes
    if content != initial_content:
        try:
            # Backup settings before writing
            backup_settings()
            # Write settings
            override_path.write_text(content)
        except OSError as e:
            logger.warning('Unable to write configuration file. %s', e)
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
        if not re.match(r'[A-Za-z][A-Za-z0-9_]*', key):
            return False, (_('Invalid setting name: %s') % key)
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

    # Get content
    try:
        initial_content = override_path.read_text()
    except FileNotFoundError:
        pass
    else:
        content = initial_content.strip()
        if content and not content.endswith('\n'):
            content += '\n'

        # Update content
        for key in keys:
            content = re.sub(fr'(^|\n)\s*{key}\s*=.+(\n|$)', r'\1', content)

        # Write changes
        if content != initial_content:
            try:
                # Backup settings before writing
                backup_settings()
                # Write settings
                if not content.strip():
                    override_path.unlink(missing_ok=True)
                else:
                    override_path.write_text(content)
            except OSError as e:
                logger.warning('Unable to write configuration file. %s' % e)
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
