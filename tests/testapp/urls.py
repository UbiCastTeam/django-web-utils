from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import TemplateView

testpatterns = (
    [
        path('', TemplateView.as_view(template_name='home.html'), name='home')
    ],
    'testapp'  # app_name
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('storage/', include(('django_web_utils.file_browser.urls', 'storage'), namespace='storage'), {'namespace': 'storage'}),
    path('monitoring/', include(('django_web_utils.monitoring.urls', 'monitoring'), namespace='monitoring')),
    path('', include(testpatterns))
]
