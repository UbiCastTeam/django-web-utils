#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Django
from django.urls import re_path
# Django web utils
from django_web_utils.file_browser import views, views_action


urlpatterns = [
    re_path(r'^$', views.storage_manager, name='file_browser_base'),
    re_path(r'^dirs/$', views.storage_dirs, name='file_browser_dirs'),
    re_path(r'^content/$', views.storage_content, name='file_browser_content'),
    re_path(r'^preview/$', views.storage_img_preview, name='file_browser_img_preview'),
    re_path(r'^action/$', views_action.storage_action, name='file_browser_action'),
]
