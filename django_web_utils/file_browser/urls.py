from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog

from django_web_utils.file_browser import views, views_action

urlpatterns = [
    path('', views.storage_manager, name='file_browser_base'),
    path('dirs/', views.storage_dirs, name='file_browser_dirs'),
    path('content/', views.storage_content, name='file_browser_content'),
    path('preview/', views.storage_img_preview, name='file_browser_img_preview'),
    path('action/', views_action.storage_action, name='file_browser_action'),
    path('jsi18n/', cache_page(3600)(
        JavaScriptCatalog.as_view(packages=['django_web_utils.file_browser'])
    ), name='file_browser_jsi18n'),
]
