#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import sys
# Django
from django.conf import settings
from django.utils.translation import gettext as _
# Django web utils
from django_web_utils.restarter import scripts

logger = logging.getLogger('djwutils.restarter.restart')


def restart_service():
    '''
    Function to call to restart the service after a few seconds.
    '''
    if getattr(settings, 'DEBUG', False):
        return True, _('The service will not be restarted because debug mode is enabled.')

    # Check that restart command is set
    if not getattr(settings, 'RESTART_COMMAND', None):
        return True, _('The service will not be restarted because no command is defined to restart it.')

    # Check that restart command is set
    if not getattr(settings, 'SITE_URL', None):
        return True, _('The service will not be restarted because no URL is defined to restart it.')

    logger.warning('Initializing restart procedure.')
    settings_mod = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not settings_mod:
        return False, _('Failed to get settings module path.')

    p_path = ':'.join([str(path) for path in sys.path if path])
    if not p_path:
        return False, _('Failed to get Python path.')

    try:
        env = dict(os.environ)
        env['PYTHONPATH'] = p_path
        env['DJANGO_SETTINGS_MODULE'] = settings_mod
        cmd = ['python3', os.path.join(scripts.__path__[0], 'daemonized_restart_requester.py')]
        p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        cmd_result = 'Exit code: %s\nOut: %s\nErr: %s' % (p.returncode, p.stdout.strip(), p.stderr.strip())
        logger.info('Restart requester script called:\n%s' % cmd_result)
        if p.returncode != 0:
            raise Exception(cmd_result)
    except Exception as e:
        return False, '%s %s' % (_('Failed to restart service:'), e)
    else:
        return True, _('The service will be restarted in 2 seconds.')
