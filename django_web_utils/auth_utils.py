#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Authentication utility functions
'''
import base64
# Django
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login


# login_required_basicauth decorator
#-------------------------------------------------------------------------------
def login_required_basicauth(function):
    '''
    Check that user is authenticated and if not, return a basic http authentication request
    '''
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated():
            return function(request, *args, **kwargs)
        
        msg = 'Access authentication'
        if request.META.get('HTTP_AUTHORIZATION'):
            to_decode = request.META['HTTP_AUTHORIZATION']
            to_decode = to_decode.split(' ')[-1]
            try:
                decoded = base64.b64decode(to_decode)
            except Exception:
                pass
            else:
                if decoded.count(':') == 1:
                    username, password = decoded.split(':')
                    # login user
                    user = authenticate(username=username, password=password)
                    if user:
                        if user.is_active:
                            login(request, user)
                            return function(request, *args, **kwargs)
                        else:
                            msg = 'Your account has been disabled !'
                    else:
                        msg = 'Your username and password were incorrect.'
        
        response = HttpResponse(msg, status=401)
        response['WWW-Authenticate'] = 'Basic realm="Access authentication"'
        return response
    return _wrapped_view

# login_basicauth function
#-------------------------------------------------------------------------------
@login_required_basicauth
def login_basicauth(request, redirect_to=None):
    rt = request.GET.get('next')
    if not rt:
        rt = redirect_to
        if not rt:
            rt = '/'
    return HttpResponseRedirect(rt)

