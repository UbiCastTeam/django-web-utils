from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from django_web_utils import json_utils
from django_web_utils.csv_utils import csv_streaming_response
from django_web_utils.magic_login.views import MagicLoginView

from .forms import FileForm, SettingsFileForm


def _handle_request(request):
    if request.method == 'POST':
        form = FileForm(request.POST, request.FILES)
        return {'valid': form.is_valid()}
    else:
        form = FileForm()
        return {'form': form.as_p()}


def view_upload(request):
    return HttpResponse(str(_handle_request(request)))


def view_forms(request):
    if request.method == 'POST':
        form = SettingsFileForm(request.POST)
        if not form.is_valid():
            success = False
            msg = 'The submitted form is incorrect. Please correct all errors in form and send it again.'
        else:
            success, msg = form.save()
    else:
        form = SettingsFileForm()
        success, msg = '', ''

    try:
        settings_file = Path(settings.OVERRIDE_PATH).read_text()
    except FileNotFoundError:
        settings_file = 'does not exist'

    return render(request, 'forms.html', {
        'form': form,
        'success': success,
        'message': msg,
        'settings_file': settings_file,
    })


def view_monitoring_widget(request):
    return render(request, 'monitoring_widget.html')


def view_csv(request):
    def csv_generator():
        yield ['Header Col1 ø', 'Header Col2 |', 'Header Col3 é']
        yield ['Row1 Col1 ,', 'Row1 Col2\n,;\'', 'Row1 Col3 à']
        yield ['Row2 Col1 ;', 'Row2 Col2\r ,;"', 'Row2 Col3 *']

    return csv_streaming_response(
        csv_generator,
        parameters=request.GET,
        file_name=request.GET.get('file_name'))


@json_utils.json_view
def view_upload_json(request):
    return JsonResponse(_handle_request(request))


class CustomMagicLoginView(MagicLoginView):
    users_json_path = Path('/tmp/djwutils/users.json')
    template_view = 'magic_login.html'

    @classmethod
    def get_users(cls):
        return {
            user.email: user
            for user in User.objects.filter(username__startswith='magic-')
        }

    @classmethod
    def create_user(cls, info):
        try:
            user = User.objects.filter(email=info['email'])[0]
        except IndexError:
            user = User(email=info['email'])
        changed = []
        for attr, val in info.items():
            if attr == 'email':
                continue
            if getattr(user, attr) != val:
                setattr(user, attr, val)
                changed.append(attr)
        if not user.id:
            user.save()
        elif changed:
            user.save(update_fields=changed)
        return user
