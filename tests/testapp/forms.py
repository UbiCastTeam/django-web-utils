#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django import forms as dj_forms

from django_web_utils.antivirus_utils import antivirus_file_validator


class FileForm(dj_forms.Form):
    file = dj_forms.FileField(label='File', required=True, validators=[antivirus_file_validator])
