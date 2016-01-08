#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Django
from django.conf.urls import url
# Django web utils
from django_web_utils.monitoring import views


urlpatterns = [
    url(r'^$', views.monitoring_panel, name='monitoring-panel'),
    url(r'^pwd/$', views.check_password, name='monitoring-check_password'),
    url(r'^status/$', views.monitoring_status, name='monitoring-status'),
    url(r'^command/$', views.monitoring_command, name='monitoring-command'),
    url(r'^conf/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_config, name='monitoring-config'),
    url(r'^logs/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_log, name='monitoring-log'),
]
