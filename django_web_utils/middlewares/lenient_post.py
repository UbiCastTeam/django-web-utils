#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class AllowEmptyContentTypePost(object):
    """
    This middleware add content type in post requests when it is missing.
    This kind of requests where forbidden in Django 1.5.
    """
    
    def process_request(self, request):
        if request.method == 'POST' and ('CONTENT_TYPE' not in request.META or request.META['CONTENT_TYPE'] == 'text/plain'):
            request.META['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        return None

