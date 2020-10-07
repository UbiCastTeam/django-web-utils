#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import subprocess
import sys
# Django
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
# Django web utils
from django_web_utils import json_utils
from django_web_utils.restarter import scripts
from django_web_utils.restarter.scripts.lib import get_signature

logger = logging.getLogger('djwutils.restarter.views')


@sensitive_post_parameters('signature')
@csrf_exempt
@json_utils.json_view(methods='POST')
def trigger_restart(request):
    '''
    When this URL is requested, the application is restarted after 2 seconds.
    Only authorized IPs can use this URL.

    Request method: POST

    Request args:

        [signature]
            The site signature.

    Response (if success):

        success
            True
    '''
    remote_addr = request.META.get('REMOTE_ADDR')
    if not remote_addr:
        return json_utils.failure_response(error='Failed to get remote address.')
    allowed_ips = getattr(settings, 'FRONT_SERVERS_IPS', None) or ['127.0.0.1']
    if remote_addr not in allowed_ips:
        raise PermissionDenied('Your IP address is not allowed to call this URL.')

    settings_mod = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not settings_mod:
        return json_utils.failure_response(error='Failed to get settings module path.')

    p_path = ':'.join([str(path) for path in sys.path if path])
    if not p_path:
        return json_utils.failure_response(error='Failed to get Python path.')

    signature = request.POST.get('signature')
    if not signature:
        raise PermissionDenied('No signature given.')
    if signature != get_signature():
        raise PermissionDenied('Incorrect signature.')

    logger.warning('A restart was requested through Django web utils API, the application will be restarted in a few seconds.\nRequester IP is "%s", settings module is "%s", Python path is "%s".', remote_addr, settings_mod, p_path)
    try:
        env = dict(os.environ)
        env['PYTHONPATH'] = p_path
        env['DJANGO_SETTINGS_MODULE'] = settings_mod
        cmd = ['python3', os.path.join(scripts.__path__[0], 'daemonized_restart_executer.py')]
        p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        cmd_result = 'Exit code: %s\nOut: %s\nErr: %s' % (p.returncode, p.stdout.strip(), p.stderr.strip())
        logger.info('Restart executer script called:\n%s' % cmd_result)
        if p.returncode != 0:
            raise Exception(cmd_result)
    except Exception as e:
        return json_utils.failure_response(error='Failed to call restart script.\n%s' % e)
    else:
        return json_utils.success_response(message='Restart script started.')
