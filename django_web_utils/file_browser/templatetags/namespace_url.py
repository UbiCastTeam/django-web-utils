#!/usr/bin/python3
# -*- coding: utf-8 -*-
from django import template
from django.core import urlresolvers

register = template.Library()


def namespace_url(namespace, view_name, *args, **kwargs):
    if namespace:
        return urlresolvers.reverse('%s:%s' % (namespace, view_name), *args, **kwargs)
    else:
        return urlresolvers.reverse(view_name, *args, **kwargs)

register.simple_tag(namespace_url)
