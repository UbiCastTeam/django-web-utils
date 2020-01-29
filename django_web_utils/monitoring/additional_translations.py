#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Additional translations
'''
# Django
from django.utils.translation import gettext_lazy as _


def _additional_translations():
    # Translations for sizes
    _('B')
    _('kB')
    _('MB')
    _('GB')
    _('TB')
