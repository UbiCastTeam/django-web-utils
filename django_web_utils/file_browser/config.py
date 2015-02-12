#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Django
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings


# Take a look at the readme file for settings descriptions

view_decorator = getattr(settings, 'FILE_BROWSER_DECORATOR', None)
if view_decorator:
    view_decorator = __import__(view_decorator)
else:
    view_decorator = user_passes_test(lambda user: user.is_staff)

BASE_PATH = getattr(settings, 'FILE_BROWSER_BASE_PATH')
BASE_URL = getattr(settings, 'FILE_BROWSER_BASE_URL')
if not BASE_URL.endswith('/'):
    BASE_URL += '/'
BASE_TEMPLATE = getattr(settings, 'FILE_BROWSER_BASE_TEMPLATE', None)
