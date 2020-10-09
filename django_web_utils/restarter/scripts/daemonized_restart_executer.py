#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to restart the service in another process.
This script allows the service to restart itself.
This script assumes that a uwsgi process is spawned after restart.
'''
import datetime
import os
import subprocess
import time
import traceback
# Django web utils
from django_web_utils.restarter.scripts import lib as sl

RESTART_AFTER = 2
CHECK_PERIOD = 5
MAX_RETRIES = 3


def execute_restart(debug):
    time.sleep(RESTART_AFTER)
    sl.log('\n\033[96m//// Starting daemonized restart executer (date: %s UTC).\033[0m' % datetime.datetime.utcnow())
    from django.conf import settings
    retry_count = 0
    atp_log = ''
    while retry_count < MAX_RETRIES:
        atp_log += 'Attempt #%s (date: %s UTC).\n' % (retry_count + 1, datetime.datetime.utcnow())
        try:
            # Get restart command
            if debug:
                cmd = ['pwd']
            else:
                cmd = getattr(settings, 'RESTART_COMMAND', None)
                if not cmd:
                    raise ValueError('The service will not be restarted because no command is defined to restart it (RESTART_COMMAND setting is not set).')
            shell = False if isinstance(cmd, (list, tuple)) else True
            cmd_repr = cmd if shell else ' '.join(cmd)
            atp_log += 'Restart command:\n%s\n' % cmd_repr

            # Clean command env
            env = dict(os.environ)
            if 'DJANGO_LOGGING' in env:
                # Drop DJANGO_LOGGING from env to get logging config from settings
                del env['DJANGO_LOGGING']
                atp_log += 'Dropped DJANGO_LOGGING in command env.\n'
            if 'UWSGI_ORIGINAL_PROC_NAME' in env:
                # Drop UWSGI_ORIGINAL_PROC_NAME from env to get allow uwsgi usage
                del env['UWSGI_ORIGINAL_PROC_NAME']
                atp_log += 'Dropped UWSGI_ORIGINAL_PROC_NAME in command env.\n'
            if 'UWSGI_RELOADS' in env:
                # Drop UWSGI_RELOADS from env to get allow uwsgi usage
                del env['UWSGI_RELOADS']
                atp_log += 'Dropped UWSGI_RELOADS in command env.\n'

            # Execute restart command
            p = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=shell)
            if p.returncode == 0:
                atp_log += 'Command done.\n'
            else:
                atp_log += 'Command failed.\n'
            atp_log += 'Code: %s\nStdout:\n%s\nStderr:\n%s\n' % (p.returncode, p.stdout.strip(), p.stderr.strip())

            # Check that the service is running
            time.sleep(CHECK_PERIOD)
            ps = subprocess.getoutput('ps x -o uid,cmd -u %s | grep -E \'^\\s*%s\'' % (os.getuid(), os.getuid()))
            if 'uwsgi ' in ps:
                atp_log += 'Service successfully restarted.\n'
                sl.log(atp_log)
                return 0
            else:
                atp_log += 'Service is not running.\n'
        except Exception:
            atp_log += 'Error during restart:\n%s\n' % traceback.format_exc()
        retry_count += 1
    sl.log(atp_log)
    sl.log('Failed to restart service after %s retries.' % retry_count)
    sl.send_email_to_admins('Service restart failed', 'Failed to restart service after %s retries.\nLog:\n%s' % (retry_count, atp_log))
    return 1


if __name__ == '__main__':
    debug = sl.init_script(__doc__)
    rc = execute_restart(debug)
    exit(rc)
