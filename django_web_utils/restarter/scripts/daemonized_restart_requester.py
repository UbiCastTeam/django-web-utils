#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to request a restart to all frontend servers.
No proxies should be used between frontend servers.
'''
import datetime
import requests
import socket
import traceback
# Django web utils
from django_web_utils.restarter.scripts import lib as sl


def request_restart(debug):
    sl.log('\n\033[96m//// Starting daemonized restart requester (date: %s UTC).\033[0m' % datetime.datetime.utcnow())
    from django.conf import settings
    from django.urls import reverse
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    hostname = socket.gethostname()
    try:
        ips = getattr(settings, 'FRONT_SERVERS_IPS', None) or ['127.0.0.1']
        if not isinstance(ips, (list, tuple)):
            sl.send_email_to_admins('Invalid configuration of FRONT_SERVERS_IPS setting in server %s.' % hostname, 'The FRONT_SERVERS_IPS value is %s.' % ips)
            return 1
        splitted_url = settings.SITE_URL.split('/')
        if len(splitted_url) < 3:
            raise ValueError('Incorrect value in SITE_URL.')
        protocol = 'http' if splitted_url[0] == 'http:' else 'https'
        host = splitted_url[2]
        if not host:
            raise ValueError('Incorrect host in SITE_URL.')
        for ip in ips:
            # Contact server by using its IP and by specifying Host to avoid load balancer
            cleaned_ip = ip if ip and not ip.startswith('127') else '127.0.0.1'
            url = '%s://%s%s' % (protocol, cleaned_ip, reverse('restarter:trigger_restart'))
            sl.log('Making request on url "%s" with Host="%s".' % (url, host))
            try:
                req = requests.post(
                    url,
                    headers=dict(Host=host),
                    data=dict(signature=sl.get_signature()),
                    proxies={'http': '', 'https': ''},
                    verify=False,
                )
                if not req.status_code == 200:
                    raise Exception('Request failed with code %s.\nContent: %s' % (req.status_code, req.text))
            except Exception as e:
                sl.log('Request to restart service failed: %s' % e)
            else:
                sl.log('Request to restart service succeeded: code %s, content: %s' % (req.status_code, req.text))
    except Exception:
        sl.send_email_to_admins('Error during restart on server %s' % hostname, traceback.format_exc())
        return 1
    return 0


if __name__ == '__main__':
    debug = sl.init_script(__doc__)
    rc = request_restart(debug)
    exit(rc)
