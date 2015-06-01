#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Additional translations
'''
# Django
from django.utils.translation import ugettext_lazy as _


def _additional_translations():
    # Translations for sizes
    _('B')
    _('KB')
    _('MB')
    _('GB')
    _('TB')
