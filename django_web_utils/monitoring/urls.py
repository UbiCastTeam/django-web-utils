#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Django
from django.urls import re_path
# Django web utils
from django_web_utils.monitoring import views


urlpatterns = [
    re_path(r'^$', views.monitoring_panel, name='monitoring-panel'),
    re_path(r'^pwd/$', views.check_password, name='monitoring-check_password'),
    re_path(r'^status/$', views.monitoring_status, name='monitoring-status'),
    re_path(r'^command/$', views.monitoring_command, name='monitoring-command'),
    re_path(r'^conf/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_config, name='monitoring-config'),
    re_path(r'^logs/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_log, name='monitoring-log'),
]
