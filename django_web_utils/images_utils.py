#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Images utility functions
'''
import os
import datetime
from PIL import Image
# utils
from .files_utils import get_new_path


# get_image_ratio function
# ----------------------------------------------------------------------------
def get_image_ratio(image_path):
    try:
        img = Image.open(image_path)
        img.load()
        size = img.size
    except Exception:
        return 0
    else:
        if size[1] > 0:
            return float(size[0]) / float(size[1])
        else:
            return 0


# get_image_info function
# ----------------------------------------------------------------------------
def get_image_info(path):
    file_size = 0
    file_extension = ''
    file_mtime = None
    if os.path.exists(path):
        file_size = os.path.getsize(path)
        file_extension = path.split('.')[-1]
        file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    
    size = (0, 0)
    try:
        img = Image.open(path)
        img.load()
        size = img.size
    except Exception:
        pass
    return dict(file_size=file_size, file_extension=file_extension, file_mtime=file_mtime, image_width=size[0], image_height=size[1])


# rotate_image function
# ----------------------------------------------------------------------------
def rotate_image(path, clockwise=True, rename=True):
    img = Image.open(path)
    img.load()
    img = img.rotate(-90 if clockwise else 90)
    if rename:
        dest = get_new_path(path)
    else:
        dest = path
    img.save(dest)
    return dest


# encode_as_jpeg function
# ----------------------------------------------------------------------------
def encode_as_jpeg(path, quality=85):
    img = Image.open(path)
    img.load()
    dest = get_new_path(path, new_extension='jpg')
    img.save(dest, 'JPEG', quality=quality)
    return dest
