#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Module used in restarter app scripts.
Warning: No Django module should be loaded in this module header.
'''
import argparse
import datetime
import hashlib
import locale
import os
import pwd
import socket
import subprocess
import sys
import uuid
# Django web utils
from django_web_utils.daemon.daemonization import daemonize


def log(text=''):
    print(text, file=sys.stdout)
    sys.stdout.flush()


def get_unix_user_name():
    return pwd.getpwuid(os.getuid()).pw_name


def send_email_to_admins(subject, content):
    from django.conf import settings
    recipients = settings.ADMINS[0][1]

    boundary = str(uuid.uuid4())
    mail = '''From: MediaServer %(user)s <noreply@ubicast.eu>
To: %(recipients)s
Subject: %(subject)s
Mime-Version: 1.0
Content-type: multipart/related; boundary="%(boundary)s"

--%(boundary)s
Content-Type: text/plain; charset=UTF-8
Content-transfer-encoding: utf-8

Date: %(date)s UTC
Server hostname: %(hostname)s
Instance name: %(user)s

%(content)s
''' % dict(
        boundary=boundary,
        user=get_unix_user_name(),
        recipients=recipients,
        subject=subject,
        date=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        hostname=socket.gethostname(),
        content=content,
    )

    p = subprocess.Popen(['/usr/sbin/sendmail', '-t'], stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
    p.communicate(input=mail.encode('utf-8'))
    if p.returncode != 0:
        log('Failed to send email.')
        return 1
    else:
        log('Email sent to: %s' % recipients)
        return 0


def get_signature():
    # Generate a signature using settings
    from django.conf import settings
    data = 'djwutils-restart-%s' % settings.SECRET_KEY
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def init_script(doc):
    # Parse args
    parser = argparse.ArgumentParser(description=doc.strip(), formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Run script in debug mode.')
    parser.add_argument('-f', '--foreground', dest='foreground', action='store_true', help='Do not daemonize.')
    args = parser.parse_args()
    # Set lang
    os.environ['LANG'] = 'C.UTF-8'
    os.environ['LC_ALL'] = 'C.UTF-8'
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    # Init Django
    os.environ['DJANGO_LOGGING'] = 'none'
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        raise ValueError('DJANGO_SETTINGS_MODULE env not set!')
    import django
    django.setup()
    from django.conf import settings
    logs_dir = getattr(settings, 'LOGS_DIR', settings.FILE_UPLOAD_TEMP_DIR)
    os.chdir(logs_dir)
    # Parse parameters
    if not args.foreground:
        # Daemonize
        log_path = os.path.join(logs_dir, 'daemonized_restart.log')
        log('Log is available in "%s".' % log_path)
        daemonize(redirect_to=log_path)
    return args.debug
