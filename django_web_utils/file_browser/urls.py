# Django
from django.urls import re_path
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog
# Django web utils
from django_web_utils.file_browser import views, views_action


urlpatterns = [
    re_path(r'^$', views.storage_manager, name='file_browser_base'),
    re_path(r'^dirs/$', views.storage_dirs, name='file_browser_dirs'),
    re_path(r'^content/$', views.storage_content, name='file_browser_content'),
    re_path(r'^preview/$', views.storage_img_preview, name='file_browser_img_preview'),
    re_path(r'^action/$', views_action.storage_action, name='file_browser_action'),
    re_path(r'^jsi18n/$', cache_page(3600)(JavaScriptCatalog.as_view(packages=['django_web_utils.file_browser'])), name='file_browser_jsi18n'),
]
