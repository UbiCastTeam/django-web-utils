#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
JSON utility functions
'''
import json
import datetime
import traceback
import logging
# Django
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


# get_date_display function
# ----------------------------------------------------------------------------
def get_date_display(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


# get_date_object function
# ----------------------------------------------------------------------------
def get_date_object(date):
    try:
        return datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


# default response function
# ----------------------------------------------------------------------------
def response(*args, **kwargs):
    code = kwargs.pop('code', 200)
    if args:
        if len(args) == 1:
            return HttpResponse(json.dumps(args[0]), content_type='application/json', status=code)
        return HttpResponse(json.dumps(args), content_type='application/json', status=code)
    return HttpResponse(json.dumps(kwargs), content_type='application/json', status=code)


# success_response function
# ----------------------------------------------------------------------------
def success_response(*args, **kwargs):
    code = kwargs.pop('code', 200)
    kwargs['success'] = True
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(json.dumps(kwargs), content_type='application/json', status=code)


# failure_response function
# ----------------------------------------------------------------------------
def failure_response(*args, **kwargs):
    code = kwargs.pop('code', 200)
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(json.dumps(kwargs), content_type='application/json', status=code)


# json_view decorator
# ----------------------------------------------------------------------------
def json_view(function=None, methods=None, login_required=False):
    '''
    Returns 400, 401, 403, 404, 405 and 500 errors in JSON format.
    The "methods" argument can be used to allow only some methods on a particular view.
    To allow several methods, use this format: "GET, PUT".
    '''
    def decorator(fct):
        def _wrapped_view(request, *args, **kwargs):
            # Check request method
            if methods and request.method not in methods:
                data = dict(error='%s (405)' % _('Invalid request method'))
                response = HttpResponse(json.dumps(data), content_type='application/json', status=405)
                response['Allow'] = methods
                return response
            # Process view
            try:
                # Check login
                if login_required and not request.user.is_authenticated:
                    return failure_response(code=401, error='%s (401)' % _('Authentication required'))
                return fct(request, *args, **kwargs)
            except PermissionDenied as e:
                return failure_response(code=403, error='%s (403)' % _('Access denied'), message=str(e))
            except Http404 as e:
                return failure_response(code=404, error='%s (404)' % _('Page not found'), message=str(e))
            except Exception:
                logger = logging.getLogger('django.request')
                logger.error('Internal server error: %s', request.get_full_path(), exc_info=traceback.extract_stack(), extra={'status_code': 500, 'request': request})
                response = failure_response(code=500, error='%s (500)' % _('Internal server error'))
                response._has_been_logged = True
                return response
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator
