#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Files utility functions
'''
import os
# Django
from django.utils.translation import ugettext_lazy as _


# get_size function
# to get size of a dir
# ----------------------------------------------------------------------------
def get_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        size = 0
        for f in os.listdir(path):
            size += get_size(os.path.join(path, f))
        return size
    else:
        # socket or something else
        return 0


# get_unit function
# ----------------------------------------------------------------------------
def get_unit(size=0, path=None):
    if path is not None:
        size = get_size(path)
    unit = _('Bytes')
    if size / 1024.0 >= 1:
        size /= 1024.0
        unit = _('KB')
        if size / 1024.0 >= 1:
            size /= 1024.0
            unit = _('MB')
            if size / 1024.0 >= 1:
                size /= 1024.0
                unit = _('GB')
                if size / 1024.0 >= 1:
                    size /= 1024.0
                    unit = _('TB')
    size = round(size, 2)
    return size, unit


# get_new_path function
# ----------------------------------------------------------------------------
def get_new_path(path, new_extension=None):
    fdir = os.path.dirname(path)
    fname = os.path.basename(path).lower()
    if '.' in path:
        splitted = fname.split('.')
        fname = '.'.join(splitted[:-1])
        if new_extension:
            fext = '.%s' % new_extension
        else:
            fext = '.%s' % splitted[-1]
    else:
        fname = fname
        fext = '.%s' % new_extension if new_extension else ''
    count = 1
    if '_' in fname:
        splitted = fname.split('_')
        try:
            count = int(splitted[-1])
        except ValueError:
            pass
        else:
            count += 1
            fname = '_'.join(splitted[:-1])
    dest = '%s/%s_%s%s' % (fdir, fname, count, fext)
    while os.path.exists(dest):
        count += 1
        dest = '%s/%s_%s%s' % (fdir, fname, count, fext)
    return dest


# remove_dir function (recursive function to remove a dir and its content)
# ----------------------------------------------------------------------------
def remove_dir(path):
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        fpath = os.path.join(path, name)
        if os.path.isfile(fpath):
            os.remove(fpath)
        elif os.path.isdir(fpath):
            remove_dir(fpath)
    os.rmdir(path)
