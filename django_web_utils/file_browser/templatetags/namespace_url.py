#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django import template
from django.urls import reverse

register = template.Library()


def namespace_url(namespace, view_name, *args, **kwargs):
    if namespace:
        return reverse('%s:%s' % (namespace, view_name), *args, **kwargs)
    else:
        return reverse(view_name, *args, **kwargs)

register.simple_tag(namespace_url)
