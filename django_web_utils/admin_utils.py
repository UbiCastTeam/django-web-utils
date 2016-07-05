#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Django admin utility functions
'''
# Django
from django.contrib import admin
from django.db import models as dj_models

SEARCH_FIELDS = (
    dj_models.CharField,
    dj_models.TextField,
    dj_models.SlugField,
)
DATE_FIELDS = (
    dj_models.DateField,
    dj_models.DateTimeField,
)
LIST_FIELDS = (
    dj_models.BooleanField,
    dj_models.NullBooleanField,
)


# register_module function
# Automatic models registeration
# ----------------------------------------------------------------------------
def register_module(models_module, options=dict()):
    for attr_name in dir(models_module):
        model = getattr(models_module, attr_name, None)
        if not hasattr(model, '__class__') or not hasattr(model, '_meta') \
           or getattr(model._meta, 'abstract', False) \
           or model in admin.site._registry \
           or not issubclass(model.__class__, dj_models.Model.__class__) \
           or not model.__module__.startswith(models_module.__name__):
            continue

        fields = []
        lfields = []
        sfields = []
        dfield = None
        for field in model._meta.fields:
            fields.append(field.name)
            if isinstance(field, LIST_FIELDS):
                lfields.append(field.name)
            if isinstance(field, SEARCH_FIELDS):
                sfields.append(field.name)
            if not dfield and isinstance(field, DATE_FIELDS):
                dfield = field.name

        class ModelOptions(admin.ModelAdmin):
            save_on_top = True
            list_display = []
            list_filter = []
            search_fields = []
            ordering = ['-id']
            date_hierarchy = None
        ModelOptions.list_display = fields
        ModelOptions.list_filter = lfields
        ModelOptions.search_fields = sfields
        ModelOptions.date_hierarchy = dfield

        if options.get(attr_name):
            for key in options[attr_name].keys():
                if hasattr(ModelOptions, key):
                    setattr(ModelOptions, key, options[attr_name][key])

        admin.site.register(model, ModelOptions)
