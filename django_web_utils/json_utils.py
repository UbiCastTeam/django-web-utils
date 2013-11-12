#!/usr/bin/env python
# -*- coding: utf-8 -*-
##-------------------------------------------------------------------------------
## Functions for MediaServer's API app
##-------------------------------------------------------------------------------
import simplejson
# Django
from django.http import HttpResponse


# get_date_display function
#-------------------------------------------------------------------------------
def get_date_display(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')

# json default response function
#-------------------------------------------------------------------------------
def response(*args, **kwargs):
    if args:
        if len(args) == 1:
            return HttpResponse(simplejson.dumps(args[0]), content_type='application/json')
        return HttpResponse(simplejson.dumps(args), content_type='application/json')
    return HttpResponse(simplejson.dumps(kwargs), content_type='application/json')

# json success_response function
#-------------------------------------------------------------------------------
def success_response(*args, **kwargs):
    kwargs['success'] = True
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(simplejson.dumps(kwargs), content_type='application/json')

# json failure_response function
#-------------------------------------------------------------------------------
def failure_response(*args, **kwargs):
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(simplejson.dumps(kwargs), content_type='application/json')

# json response_404 function
#-------------------------------------------------------------------------------
def response_404(*args, **kwargs):
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(simplejson.dumps(kwargs), content_type='application/json', status=404)

# json response_403 function
#-------------------------------------------------------------------------------
def response_403(*args, **kwargs):
    kwargs['success'] = False
    if args:
        if len(args) == 1:
            kwargs['data'] = args[0]
        else:
            kwargs['data'] = args
    return HttpResponse(simplejson.dumps(kwargs), content_type='application/json', status=403)

