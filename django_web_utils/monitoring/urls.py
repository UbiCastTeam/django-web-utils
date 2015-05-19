#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Django
from django.conf.urls import patterns, url


urlpatterns = patterns(
    'django_web_utils.monitoring.views',  # prefix
    url(r'^$', 'monitoring_panel', name='monitoring-panel'),
    url(r'^status/$', 'monitoring_status', name='monitoring-status'),
    url(r'^command/$', 'monitoring_command', name='monitoring-command'),
    url(r'^conf/(?P<name>[-_\w\d]{1,255})/$', 'monitoring_config', name='monitoring-config'),
    url(r'^logs/(?P<name>[-_\w\d]{1,255})/$', 'monitoring_log', name='monitoring-log'),
)
