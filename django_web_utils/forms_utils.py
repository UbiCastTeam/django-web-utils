#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Forms utility functions
'''
import os
import logging
# Django
from django import forms as dj_forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# Django web utils
from django_web_utils.settings_utils import set_settings

logger = logging.getLogger('djwutils.forms_utils')


class FileInfo():
    def __init__(self, path):
        self.name = os.path.basename(path) if path else ''
        self.url = '#'  # if no url, the value is ignored in the Django widget

    def __str__(self):
        return self.name


class NoLinkClearableFileInput(dj_forms.ClearableFileInput):
    '''
    Widget for a file upload without link to the file.
    '''

    def render(self, name, value, *args, **kwargs):
        obj_value = FileInfo(value) if isinstance(value, str) else value
        return super().render(name, obj_value, *args, **kwargs)


class PasswordToggleInput(dj_forms.TextInput):
    '''
    Widget to allow user to toggle a password input between text or password type.
    '''
    template_name = 'forms_utils/password_toggle_input.html'
    orig_template_name = dj_forms.TextInput.template_name

    def get_context(self, name, value, attrs):
        data = super().get_context(name, value, attrs)
        data['widget']['orig_template_name'] = self.orig_template_name
        data['widget']['type'] = 'hidden'
        data['widget']['hidden_value'] = '●' * len(value)
        return data


class ProtectedFileField(dj_forms.FileField):
    '''
    A field for a file which is not accessible for the user.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(widget=NoLinkClearableFileInput(), *args, **kwargs)

    @classmethod
    def handle_uploaded_file(cls, ufile, upload_to, validator=None):
        if ufile is None or not upload_to:
            return None
        if ufile:
            if not os.path.exists(os.path.dirname(upload_to)):
                os.makedirs(os.path.dirname(upload_to), exist_ok=True)
                tmp_path = upload_to + '.tmp'
            else:
                number = 0
                tmp_path = None
                while not tmp_path:
                    tmp_path = upload_to + '.tmp' + str(number)
                    number += 1
                    if os.path.exists(tmp_path):
                        tmp_path = None
            with open(tmp_path, 'wb+') as fd:
                for chunk in ufile.chunks():
                    fd.write(chunk)
            if validator:
                try:
                    validator(tmp_path)
                except Exception:
                    os.remove(tmp_path)
                    raise
            os.rename(tmp_path, upload_to)
            return True
        else:
            if os.path.exists(upload_to):
                os.remove(upload_to)
            return False


class BaseFileSettingsForm(object):
    '''
    Form designed to change settings file values and restart server then.
    Settings that can be altered must be defined in Meta.SETTINGS_MAPPING.
    '''

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', dict())
        for field, info in self.Meta.SETTINGS_MAPPING.items():
            if field not in initial:
                val = getattr(settings, info['setting'], info['default'])
                if isinstance(val, str) and '\n' in val and '\r' not in val:
                    # browsers injects \r in multi lines texts so do it before to have a correct changed_data value
                    val = val.replace('\n', '\r\n')
                initial[field] = val
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    class Meta:
        SETTINGS_MAPPING = {
            # <field>: {'setting': <name>, 'default': <default>}
        }

        @classmethod
        def get_default_values(cls, mapping):
            default_values = dict()
            for field, info in mapping.items():
                if info['default'] is True:
                    default_values[field] = _('Yes')
                elif info['default'] is False:
                    default_values[field] = _('No')
                elif info['default']:
                    default_values[field] = info['default']
            return default_values

    def save(self, commit=True):
        '''
        Returns: success (boolean), changed (list of fields names).
        '''
        if hasattr(super(), 'save'):
            super().save(commit)
        # Settings fields
        changed = list()
        for field, info in self.Meta.SETTINGS_MAPPING.items():
            value = self.cleaned_data.get(field, info['default'])
            if not value and info['default'] is None and getattr(settings, info['setting'], None) is None:
                continue
            if getattr(settings, info['setting'], info['default']) != value:
                changed.append((info['setting'], value))
        # Write settings file
        if commit:
            return set_settings(changed)
        return True, changed


class FileSettingsForm(BaseFileSettingsForm, dj_forms.Form):
    pass


class FileSettingsModelForm(BaseFileSettingsForm, dj_forms.ModelForm):
    pass
