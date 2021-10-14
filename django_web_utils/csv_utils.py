#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
CSV utility functions
'''
from io import StringIO
import csv
# Django
from django.http import HttpResponse


class CSVFile():
    '''
    Simple class to generate a CSV response.
    If a request object is given, some settings will be get from request.GET:
        delimiter, quote and encoding
    '''

    def __init__(self, request=None):
        delimiter = request.GET['delimiter'][0] if request and request.GET.get('delimiter') else ','
        quotechar = request.GET['quote'][0] if request and request.GET.get('quote') else '"'
        quotechar = quotechar if quotechar != delimiter else ('\'' if quotechar == '"' else '"')
        self.csv_file = StringIO()
        self.csv_writer = csv.writer(self.csv_file, delimiter=delimiter, quotechar=quotechar, quoting=csv.QUOTE_MINIMAL)
        self.charset = 'cp1252' if request and request.GET.get('encoding') == 'cp1252' else 'utf-8'

    def write_row(self, columns):
        self.csv_writer.writerow(columns)

    def write_line_break(self, lines=1):
        self.csv_file.write('\r\n' * lines)

    def get_text(self):
        csv_content = self.csv_file.getvalue().encode(self.charset, 'replace')
        return csv_content

    def get_response(self, file_name=None):
        csv_content = self.get_text()
        response = HttpResponse(csv_content, content_type='text/csv; charset=' + self.charset)
        if file_name:
            response['Content-Disposition'] = 'attachment; filename="%s"' % file_name
        return response
