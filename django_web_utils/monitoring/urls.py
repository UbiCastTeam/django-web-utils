#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Django
from django.urls import re_path
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog
# Django web utils
from django_web_utils.monitoring import views


urlpatterns = [
    re_path(r'^$', views.monitoring_panel, name='monitoring-panel'),
    re_path(r'^pwd/$', views.check_password, name='monitoring-check_password'),
    re_path(r'^status/$', views.monitoring_status, name='monitoring-status'),
    re_path(r'^command/$', views.monitoring_command, name='monitoring-command'),
    re_path(r'^conf/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_config, name='monitoring-config'),
    re_path(r'^logs/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_log, name='monitoring-log'),
    re_path(r'^jsi18n/$', cache_page(3600)(JavaScriptCatalog.as_view(packages=['django_web_utils.monitoring'])), name='monitoring-jsi18n'),
]
