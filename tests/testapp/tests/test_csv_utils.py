import pytest

from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('charset', ['utf-8', 'cp1252'])
def test_csv_response__default_parameters(client, charset):
    response = client.get(
        reverse('testapp:csv'),
        {'encoding': charset})
    assert response.status_code == 200
    assert response['Content-Type'] == f'text/csv; charset={charset}'
    assert response['Content-Encoding'] == 'identity'
    assert response['X-Accel-Buffering'] == 'no'
    assert response['X-Accel-Charset'] == charset
    expected = [
        'Header Col1 ø,Header Col2 |,Header Col3 é\r\n',
        '"Row1 Col1 ,","Row1 Col2 ,;\'",Row1 Col3 à\r\n',
        'Row2 Col1 ;,"Row2 Col2 ,;""",Row2 Col3 *\r\n',
    ]
    actual = [row.decode(charset) for row in response.streaming_content]
    assert actual == expected


@pytest.mark.parametrize('charset', ['utf-8', 'cp1252'])
def test_csv_response__custom_parameters(client, charset):
    response = client.get(
        reverse('testapp:csv'),
        {'encoding': charset, 'delimiter': ';', 'quote': "'"})
    assert response.status_code == 200
    assert response['Content-Type'] == f'text/csv; charset={charset}'
    assert response['Content-Encoding'] == 'identity'
    assert response['X-Accel-Buffering'] == 'no'
    assert response['X-Accel-Charset'] == charset
    expected = [
        'Header Col1 ø;Header Col2 |;Header Col3 é\r\n',
        'Row1 Col1 ,;\'Row1 Col2 ,;\'\'\';Row1 Col3 à\r\n',
        '\'Row2 Col1 ;\';\'Row2 Col2 ,;"\';Row2 Col3 *\r\n',
    ]
    actual = [row.decode(charset) for row in response.streaming_content]
    assert actual == expected
