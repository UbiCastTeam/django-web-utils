#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Models utility functions
'''
import os
import sys

from django.core.cache import cache


class SingletonModel(object):
    '''
    The model using this should inherit SingletonModel first.
    For example:
        class SiteSettings(SingletonModel, models.Model)
    The model is stored in cache and depends on file mtime.
    '''
    SINGLETON_CACHE = True

    def __init__(self, *args, **kwargs):
        # since Django Model is inherited as second,
        # super will call the Django Model method
        super(SingletonModel, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # since Django Model is inherited as second,
        # super will call the Django Model method
        result = super(SingletonModel, self).save(*args, **kwargs)
        if self.SINGLETON_CACHE:
            cache_key = self.__class__.get_singleton_cache_key()
            mtime = self.__class__.get_singleton_class_mtime()
            cache.set(cache_key, (mtime, self), timeout=25 * 3600)
        return result

    @classmethod
    def get_singleton_cache_key(cls):
        return 'SingletonModel-%s' % cls.__name__

    @classmethod
    def get_singleton_class_mtime(cls):
        mtime = getattr(cls, '_class_mtime', None)
        if not mtime:
            if cls.__module__ in sys.modules:
                class_path = os.path.abspath(sys.modules[cls.__module__].__file__)
                mtime = os.path.getmtime(class_path)
            else:
                # fallback: use class id as mtime
                # can happen for fake class
                mtime = id(cls)
            cls._class_mtime = mtime
        return mtime

    @classmethod
    def get_singleton(cls):
        if cls.SINGLETON_CACHE:
            cache_key = cls.get_singleton_cache_key()
            mtime = cls.get_singleton_class_mtime()
            cached = cache.get(cache_key)
            if cached and isinstance(cached, tuple) and cached[0] == mtime:
                return cached[1]
        try:
            obj = cls.objects.all()[0]
        except IndexError:
            obj = cls.objects.create()
        if cls.SINGLETON_CACHE:
            cache.set(cache_key, (mtime, obj), timeout=25 * 3600)
        return obj
