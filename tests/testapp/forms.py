#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django import forms as dj_forms

from django_web_utils.antivirus_utils import antivirus_stream_validator
from django_web_utils.settings_store.forms import SettingsStoreForm
from testapp.models import SettingsStore


class FileForm(dj_forms.Form):
    file = dj_forms.FileField(label='File', required=True, validators=[antivirus_stream_validator])


class SettingsStoreValForm(SettingsStoreForm):
    str_val = dj_forms.CharField(label='String value', max_length=100, required=False)
    float_val = dj_forms.FloatField(label='Float value', min_value=0, required=False)

    class Meta(SettingsStoreForm.Meta):
        SETTINGS_STORE_MAPPING = {
            'str_val': {'setting': 'STR_VAL'},
            'float_val': {'setting': 'FLOAT_VAL'},
        }
        default_values = SettingsStoreForm.Meta.get_default_values(SettingsStore, SETTINGS_STORE_MAPPING)
