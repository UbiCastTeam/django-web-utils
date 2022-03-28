'''
Time utils tests.
'''
import pytest
from contextlib import nullcontext

from django_web_utils.time_utils import get_hms_tuple, get_hms_str


@pytest.mark.parametrize('value,expectation,expected', [
    pytest.param(-1, pytest.raises(ValueError), None, id='negative_raises'),
    pytest.param(0, nullcontext(), (0, 0, 0), id='0'),
    pytest.param(50, nullcontext(), (0, 0, 50), id='50'),
    pytest.param(130, nullcontext(), (0, 2, 10), id='130'),
    pytest.param(4250, nullcontext(), (1, 10, 50), id='4250')
])
def test_get_hms_tuple(value, expectation, expected):
    with expectation:
        assert get_hms_tuple(value) == expected


@pytest.mark.parametrize('value,expected', [
    pytest.param(0, '0s'),
    pytest.param(40, '40s'),
    pytest.param(150, '2m 30s'),
    pytest.param(3670, '1h 1m 10s')
])
def test_get_hms_str(value, expected):
    assert get_hms_str(value) == expected
