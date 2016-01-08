#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Django
from django.conf.urls import url
# Django web utils
from django_web_utils.file_browser import views, views_action


urlpatterns = [
    url(r'^$', views.storage_manager, name='file_browser_base'),
    url(r'^dirs/$', views.storage_dirs, name='file_browser_dirs'),
    url(r'^content/$', views.storage_content, name='file_browser_content'),
    url(r'^preview/$', views.storage_img_preview, name='file_browser_img_preview'),
    url(r'^action/$', views_action.storage_action, name='file_browser_action'),
]
