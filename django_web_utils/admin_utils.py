#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Django admin utility functions
'''
import csv
# Django
from django.contrib import admin
from django.db import models as dj_models
from django.http import HttpResponse


def _export_as_csv_action(description="Export selected objects as CSV file", fields=None, exclude=None, header=True):
    """
    This function returns an export csv action
    'fields' and 'exclude' work like in django ModelForm
    'header' is whether or not to output the column names as the first row
    """
    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        opts = modeladmin.model._meta
        field_names = set([field.name for field in opts.fields])

        if fields:
            fieldset = set(fields)
            field_names = field_names & fieldset

        elif exclude:
            excludeset = set(exclude)
            field_names = field_names - excludeset

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=export.csv'

        writer = csv.writer(response)

        if header:
            writer.writerow(list(field_names))
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = description
    return export_as_csv


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
            actions = []
            list_display = []
            list_filter = []
            search_fields = []
            ordering = ['-id']
            date_hierarchy = None
        ModelOptions.list_display = fields
        ModelOptions.list_filter = lfields
        ModelOptions.search_fields = sfields
        ModelOptions.date_hierarchy = dfield
        ModelOptions.actions = [_export_as_csv_action("CSV Export", fields=fields)]

        if options.get(attr_name):
            for key in options[attr_name].keys():
                if hasattr(ModelOptions, key):
                    setattr(ModelOptions, key, options[attr_name][key])

        admin.site.register(model, ModelOptions)
