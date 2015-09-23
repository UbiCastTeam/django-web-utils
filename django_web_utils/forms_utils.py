#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Forms utility functions
'''
import os
import logging
logger = logging.getLogger('djwutils.forms_utils')
# Django
from django import forms as dj_forms


# FileInfo field
# ----------------------------------------------------------------------------
class FileInfo():
    def __init__(self, path):
        self.name = os.path.basename(path) if path else ''
        self.url = ''

    def __str__(self):
        return self.name


# NoLinkClearableFileInput field
# ----------------------------------------------------------------------------
class NoLinkClearableFileInput(dj_forms.ClearableFileInput):
    url_markup_template = '<b>{1}</b>'

    def render(self, name, value, attrs=None):
        obj_value = FileInfo(value) if isinstance(value, (str, unicode)) else value
        return super(NoLinkClearableFileInput, self).render(name, obj_value, attrs)


# ProtectedFileField field
# ----------------------------------------------------------------------------
class ProtectedFileField(dj_forms.FileField):
    '''
    A field for a file which is not accessible for the user.
    '''

    def __init__(self, *args, **kwargs):
        super(ProtectedFileField, self).__init__(widget=NoLinkClearableFileInput(), *args, **kwargs)

    @classmethod
    def handle_uploaded_file(cls, ufile, upload_to, validator=None):
        if ufile is None or not upload_to:
            return None
        if ufile:
            if not os.path.exists(os.path.dirname(upload_to)):
                os.makedirs(os.path.dirname(upload_to))
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
