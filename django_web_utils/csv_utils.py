"""
CSV utility functions
"""
from collections.abc import Iterable
# Django
from django.http import StreamingHttpResponse


def csv_streaming_response(
    rows_iterator: Iterable, parameters: dict = None, file_name: str = None
) -> StreamingHttpResponse:
    """
    Simple function to stream a CSV file.
    The "rows_iterator" should send a list for each CSV row.
    If a parameters dict is given, some settings will be retrieved from it:
        delimiter, quote and encoding
    """
    delimiter = parameters['delimiter'][0] if parameters and parameters.get('delimiter') else ','
    quotechar = parameters['quote'][0] if parameters and parameters.get('quote') else '"'
    if quotechar == delimiter:
        quotechar = "'" if quotechar == '"' else '"'
    charset = 'cp1252' if parameters and parameters.get('encoding') == 'cp1252' else 'utf-8'

    def clean_value(val):
        cleaned = val if isinstance(val, str) else str(val)
        cleaned = cleaned.replace('\r', '')
        cleaned = cleaned.replace('\n', ' ')
        if delimiter in cleaned:
            cleaned = cleaned.replace(quotechar, quotechar + quotechar)
            cleaned = quotechar + cleaned + quotechar
        return cleaned

    def iterator():
        for row in rows_iterator():
            yield (delimiter.join([clean_value(val) for val in row]) + '\r\n').encode(charset, 'replace')

    response = StreamingHttpResponse(iterator(), content_type=f'text/csv; charset={charset}')
    if file_name:
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response['Content-Encoding'] = 'identity'
    response['X-Accel-Buffering'] = 'no'
    response['X-Accel-Charset'] = charset
    return response
