#!/usr/bin/env python
# -*- coding: utf-8 -*-
##-------------------------------------------------------------------------------
## Functions for MediaServer's API app
##-------------------------------------------------------------------------------
import json
import datetime
import traceback
import logging
# Django
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext_lazy as _


# get_date_display function
#-------------------------------------------------------------------------------
def get_date_display(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')

# get_date_object function
#-------------------------------------------------------------------------------
def get_date_object(date):
    try:
        return datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

# default response function
#-------------------------------------------------------------------------------
def response(*args, **kwargs):
    code = kwargs.pop('code', 200)
    if args:
        if len(args) == 1:
            return HttpResponse(json.dumps(args[0]), content_type='application/json', status=code)
        return HttpResponse(json.dumps(args), content_type='application/json', status=code)
    return HttpResponse(json.dumps(kwargs), content_type='application/json', status=code)

# success_response function
#-------------------------------------------------------------------------------
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
#-------------------------------------------------------------------------------
def failure_response(*args, **kwargs):
    code = kwargs.pop('code', 200)
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(json.dumps(kwargs), content_type='application/json', status=code)


# classic errors classes
#-------------------------------------------------------------------------------
JsonHttp404 = Http404

class JsonHttp401(Exception):
    pass

class JsonHttp403(Exception):
    pass

class JsonHttp400(Exception):
    pass


# json_view function
#-------------------------------------------------------------------------------
def json_view(methods=None):
    '''
    Returns 400, 403, 404 and 500 errors in JSON format.
    The "methods" argument can be used to allow only some methods on a particular view.
    '''
    def _wrap(function):
        def _wrapped_view(request, *args, **kwargs):
            # check request method
            if methods and (((isinstance(methods, list) or isinstance(methods, tuple)) and request.method not in methods) or request.method != methods):
                data = dict(error=u'%s (405)' %_('Invalid request method'))
                response = HttpResponse(json.dumps(data), content_type='application/json', status=405)
                response['Allow'] = ', '.join(methods) if isinstance(methods, list) or isinstance(methods, tuple) else methods
                return response
            # process view
            try:
                return function(request, *args, **kwargs)
            except JsonHttp400:
                return failure_response(code=400, error=u'%s (400)' %_('Bad request'))
            except JsonHttp401:
                return failure_response(code=401, error=u'%s (401)' %_('Authentication required'))
            except JsonHttp403:
                return failure_response(code=403, error=u'%s (403)' %_('Access denied'))
            except JsonHttp404:
                return failure_response(code=404, error=u'%s (404)' %_('Page not found'))
            except Exception:
                logger = logging.getLogger('django.request')
                logger.error('Internal server error: %s\n%s', request.path, traceback.format_exc(), extra={'status_code': 500, 'request': request})
                return failure_response(code=500, error=u'%s (500)' %_('Internal server error'))
        return _wrapped_view
    return _wrap

