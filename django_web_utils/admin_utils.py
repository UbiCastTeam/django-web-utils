#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Django admin utility functions
'''
# Django
from django.contrib import admin
from django.db import models as dj_models


# register_module function
# Automatic models registeration
# ----------------------------------------------------------------------------
def register_module(models_module):
    for attr_name in dir(models_module):
        model = getattr(models_module, attr_name, None)
        if not hasattr(model, '__class__') or not hasattr(model, '_meta') \
            or getattr(model._meta, 'abstract', False) \
            or model in admin.site._registry \
            or not issubclass(model.__class__, dj_models.Model.__class__) \
            or not model.__module__.startswith(models_module.__name__):
            continue
        
        fields = []
        for field in model._meta.fields:
            fields.append(field.name)

        class ModelOptions(admin.ModelAdmin):
            save_on_top = True
            list_display = []
            list_filter = []
            ordering = ['-id']
        ModelOptions.list_display = fields
        
        admin.site.register(model, ModelOptions)
