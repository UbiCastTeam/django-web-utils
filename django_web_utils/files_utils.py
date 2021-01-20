#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Files utility functions
'''
import os
import subprocess
# Django
from django.utils.translation import gettext_lazy as _


# get_size function
# to get size of a dir
# ----------------------------------------------------------------------------
def get_size(path, ignore_du_errors=True):
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        # "du" is much faster than getting size file of all files using python
        p = subprocess.run(['du', '-sb', path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        out = p.stdout.decode('utf-8').strip()
        err = p.stderr.decode('utf-8').strip()
        if not ignore_du_errors and p.returncode != 0:
            raise Exception('Failed to get size using "du". Stdout: %s, Stderr: %s' % (out, err))
        try:
            return int(out.split('\t')[0])
        except Exception:
            raise Exception('Failed to get size using "du". Stdout: %s, Stderr: %s' % (out, err))
    else:
        # socket or something else
        return 0


# get_unit function
# ----------------------------------------------------------------------------
def get_unit(size=0, path=None):
    if path is not None:
        size = get_size(path)
    if abs(size) <= 1000:
        unit = _('B')
    else:
        size /= 1000.0
        if abs(size) <= 1000:
            unit = _('kB')
        else:
            size /= 1000.0
            if abs(size) <= 1000:
                unit = _('MB')
            else:
                size /= 1000.0
                if abs(size) <= 1000:
                    unit = _('GB')
                else:
                    size /= 1000.0
                    unit = _('TB')
    size = round(size, 1)
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


# remove_dir function
# (recursive function to remove a dir and its content)
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


# reverse_readline function
# (to read a file from its end without loading it competely)
# ----------------------------------------------------------------------------
def reverse_read(filename, buf_size=8192):
    # utf-8 decoding is not in this function to avoid splitting unicode characters.
    with open(filename, 'rb') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        total_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(total_size, offset + buf_size)
            fh.seek(-offset, os.SEEK_END)
            segment = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            yield segment
        yield None
