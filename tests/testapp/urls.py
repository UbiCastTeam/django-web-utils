from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path, re_path
from django.contrib import admin
from django.views.generic import TemplateView
from django.views.static import serve

from . import views

admin.autodiscover()

testpatterns = (
    [
        path('', TemplateView.as_view(template_name='home.html'), name='home'),
        path('magic/', views.CustomMagicLoginView.as_view(), name='magic_login'),
        path('upload/', views.test_upload, name='upload'),
        path('upload/json/', views.test_upload_json, name='upload_json'),
        path('forms/', views.test_forms, name='forms'),
        path('csv/', views.test_csv, name='csv'),
        re_path(r'^storage/(?P<path>.*)$', serve, {
            'document_root': settings.FILE_BROWSER_DIRS['storage'][0],
            'show_indexes': settings.DEBUG
        }, name='storage'),
    ],
    'testapp'  # app_name
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('storage-browser/', include(('django_web_utils.file_browser.urls', 'storage'), namespace='storage'), {'namespace': 'storage'}),
    path('monitoring/', include(('django_web_utils.monitoring.urls', 'monitoring'), namespace='monitoring')),
    path('', include(testpatterns)),
]
