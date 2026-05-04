from django.urls import path, re_path
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog

from django_web_utils.monitoring import views


urlpatterns = [
    path('', views.monitoring_panel, name='monitoring-panel'),
    path('status/', views.monitoring_status, name='monitoring-status'),
    path('command/', views.monitoring_command, name='monitoring-command'),
    re_path(r'^logs/(?P<name>[-_\w\d]{1,255})/$', views.monitoring_log, name='monitoring-log'),
    path('jsi18n/', cache_page(3600)(
        JavaScriptCatalog.as_view(packages=['django_web_utils.monitoring'])
    ), name='monitoring-jsi18n'),
]
