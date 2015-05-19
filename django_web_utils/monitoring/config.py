#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Django
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings


# Take a look at the readme file for settings descriptions

def _import(module):
    if '.' in module:
        element = module.split('.')[-1]
        _tmp = __import__(module[:-len(element) - 1], fromlist=[element])
        return getattr(_tmp, element)
    else:
        return __import__(module)


view_decorator = getattr(settings, 'MONITORING_VIEWS_DECORATOR', None)
if view_decorator:
    view_decorator = _import(view_decorator)
else:
    view_decorator = user_passes_test(lambda user: user.is_staff)

BASE_TEMPLATE = getattr(settings, 'MONITORING_BASE_TEMPLATE', None)

info_module = getattr(settings, 'MONITORING_DAEMONS_INFO', None)
if info_module:
    info_module = _import(info_module)
