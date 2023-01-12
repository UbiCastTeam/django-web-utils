from django.http import JsonResponse, HttpResponse

from django_web_utils import json_utils
from django_web_utils.csv_utils import csv_streaming_response

from .forms import FileForm


def _handle_request(request):
    if request.method == 'POST':
        form = FileForm(request.POST, request.FILES)
        return {'valid': form.is_valid()}
    else:
        form = FileForm()
        return {'form': form.as_p()}


def test_upload(request):
    return HttpResponse(str(_handle_request(request)))


def test_csv(request):
    def csv_generator():
        yield ['Header Col1 ø', 'Header Col2 |', 'Header Col3 é']
        yield ['Row1 Col1 ,', 'Row1 Col2 ,;\'', 'Row1 Col3 à']
        yield ['Row2 Col1 ;', 'Row2 Col2 ,;"', 'Row2 Col3 *']

    return csv_streaming_response(
        csv_generator,
        parameters=request.GET,
        file_name=request.GET.get('file_name'))


@json_utils.json_view
def test_upload_json(request):
    return JsonResponse(_handle_request(request))
