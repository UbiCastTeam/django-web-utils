#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to test daemonization.

Usage: <script name> [restart|stop] [<user name>]
"""
import datetime
import os
import subprocess
import sys
import time
# Django web utils
from django_web_utils.daemon.daemonization import daemonize

LOG_PATH = os.path.abspath(os.path.expanduser('/tmp/daemonization_test.log'))


def _log(text=''):
    print(text, file=sys.stdout)
    sys.stdout.flush()


def _exec(*args):
    _log('>>> %s' % ' '.join(args))
    shell = len(args) == 1 and '|' in args[0]
    p = subprocess.run(args, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr, shell=shell)
    sys.stdout.flush()
    return p.returncode


if __name__ == '__main__':
    now = datetime.datetime.now()
    # Check that the script is not running
    _log('Checking that the script is not currently running...')
    rc = _exec('ps aux | grep -v grep | grep -v " %s " | grep %s' % (os.getpid(), os.path.basename(__file__)))
    if rc == 0:
        print('The script is already running.', file=sys.stderr)
        sys.exit(1)
    _log('OK')
    # Get command
    action = sys.argv[1] if len(sys.argv) > 1 else 'restart'
    if action not in ('restart', 'stop'):
        print('Invalid action requested.', file=sys.stderr)
        sys.exit(1)
    # Daemonize
    wd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    daemonize(redirect_to=LOG_PATH, rundir=wd)
    sys.path.append(wd)
    # Write initial info in log
    _log('Started on %s.' % (now.strftime('%Y-%m-%d %H:%M:%S')))
    _log('\n---- ps aux ----\n')
    _exec('ps aux | grep -v grep | grep watch')
    _log('\n---- killing ----\n')
    rc = _exec('pkill', '-f', '--', 'watch date')
    _log('pkill return code: %s' % rc)
    if action == 'stop':
        sys.exit(0)
    time.sleep(1)
    print('---------')
    os.environ = dict()
    print(str(os.environ))
    _exec('lsof', '-p', str(os.getpid()))
    print('---------')
    sys.stdout.flush()

    _log('\n---- Starting external command ----\n')
    os.fsync(1)
    os.fsync(2)
    os.execl('/usr/bin/watch', 'watch', 'date')
