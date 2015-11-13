#!/usr/bin/python3
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
            obj = cls.objects.create()
        return obj
