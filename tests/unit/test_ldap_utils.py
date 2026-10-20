from unittest import mock

import pytest

from django_web_utils import ldap_utils


def test_get_conf(settings):
    assert ldap_utils.get_conf('USER_ID_FIELD') == 'uid'
    settings.AUTH_LDAP_USER_ID_FIELD = 'sAMAccountName'
    assert ldap_utils.get_conf('USER_ID_FIELD') == 'sAMAccountName'


def test_get_user_info__filter_escaped():
    with mock.patch.object(ldap_utils, 'ldap_search', return_value=[{'dn': 'uid=a', 'attributes': {}}]) as search:
        ldap_utils.get_user_info('a*)(uid=*', connection=object())
    assert search.call_args.args[1] == r'(&(objectClass=person)(uid=a\2a\29\28uid=\2a))'


@pytest.mark.parametrize('error_on', ['authenticate', 'groups'])
def test_test_ldap_connection__escaped(error_on):
    html_error = Exception('<script>alert(1)</script>')
    user_info = {'uid': ['<b>user</b>']}
    patches = {
        'get_connection': mock.Mock(return_value=object()),
        'get_user_info': mock.Mock(return_value=('uid=user', user_info)),
        'authenticate': mock.Mock(side_effect=html_error if error_on == 'authenticate' else None),
        'get_user_groups': mock.Mock(
            side_effect=html_error if error_on == 'groups' else None,
            return_value={'cn=<i>group</i>': {'cn': ['<i>group</i>']}},
        ),
    }
    with mock.patch.multiple(ldap_utils, **patches):
        success, msg = ldap_utils.test_ldap_connection('<u>user</u>', password='pwd', get_groups=True)
    assert success is False
    assert '<script>' not in msg
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in msg
    assert '<b>user</b>' not in msg
    assert '<i>group</i>' not in msg
    assert '<u>' not in msg
