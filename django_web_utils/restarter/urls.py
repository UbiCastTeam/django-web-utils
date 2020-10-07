#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Django
from django.urls import path
# Django web utils
from django_web_utils.restarter import views


urlpatterns = [
    path('', views.trigger_restart, name='trigger_restart'),
]
