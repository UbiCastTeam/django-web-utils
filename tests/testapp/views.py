#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.http import JsonResponse, HttpResponse

from django_web_utils import json_utils

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


@json_utils.json_view
def test_upload_json(request):
    return JsonResponse(_handle_request(request))
