#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Models utility functions
'''


class SingletonModel():

    @classmethod
    def get_singleton(cls):
        try:
            obj = cls.objects.all()[0]
        except IndexError:
            obj = cls()
            obj.save()
        return obj