#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Django
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings


# Mandatory settings:
# FILE_BROWSER_BASE_PATH: base path to server with file browser
# FILE_BROWSER_BASE_URL: base url for served files
# Optional settings:
# FILE_BROWSER_DECORATOR: function python path to be used as decorator
# BASE_VIEW: the view to use as base page
#   If you want to use a custom view, make sure you have
#   imported jquery.js, utils.js, odm.css and odm.js


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
