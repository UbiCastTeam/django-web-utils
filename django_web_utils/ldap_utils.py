#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
LDAP utility functions
'''
import ldap3
import logging
import ssl
# Django
from django.conf import settings
from django.template import defaultfilters
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger('djwutils.ldap_utils')


# Prepare LDAP settings object
class LDAPSettings(object):
    SERVER_URI = 'ldap://server.net'
    USER_SEARCH_SCOPE = 'ou=People,dc=server,dc=net'
    USER_SEARCH_FILTER = '(uid=%(user)s)'
    ALWAYS_UPDATE = True
    EMAIL_FIELD = 'mail'
    START_TLS = False
    TLS_VERSION = None
    CHECK_CERT = True
    SEARCH_LIMIT = 50000
    CA_CERT = None
    USE_SASL = False
    BIND_DN = ''
    BIND_PASSWORD = ''
    TIEMOUT = 15
lsettings = LDAPSettings


# update_settings function
# ----------------------------------------------------------------------------
def update_ldap_settings(s, prefix=None):
    if not prefix:
        prefix = 'AUTH_LDAP'
    if isinstance(s, dict):
        for name in dir(LDAPSettings):
            if not name.startswith('_') and '%s_%s' % (prefix, name) in s:
                setattr(lsettings, name, s['%s_%s' % (prefix, name)])
    else:
        for name in dir(LDAPSettings):
            if not name.startswith('_') and hasattr(s, '%s_%s' % (prefix, name)):
                setattr(lsettings, name, getattr(s, '%s_%s' % (prefix, name)))

# Update settings with Django settings file
update_ldap_settings(settings, getattr(settings, 'LDAP_SETTINGS_PREFIX', None))


# get_connection function
# ----------------------------------------------------------------------------
def get_connection(bind_dn=None, bind_password=None):
    try:
        sv_params = dict(host=lsettings.SERVER_URI, use_ssl=lsettings.SERVER_URI.startswith('ldaps://'))
        if lsettings.START_TLS:
            tls_params = dict()
            if lsettings.CHECK_CERT:
                tls_params = dict(validate=ssl.CERT_REQUIRED)
            else:
                tls_params = dict(validate=ssl.CERT_OPTIONAL)
            if lsettings.TLS_VERSION == 'v1':
                tls_params['version'] = ssl.PROTOCOL_TLSv1
            else:
                tls_params['version'] = ssl.PROTOCOL_SSLv3
            if lsettings.CA_CERT:
                tls_params['ca_certs_file'] = ssl.CA_CERT
            tls = ldap3.Tls(**tls_params)
            sv_params['tls'] = tls
            sv_params['use_ssl'] = True
        server = ldap3.Server(**sv_params)
    except Exception as e:
        raise Exception('%s\n%s %s' % (_('Error when initializing connection with LDAP server.'), _('Error:'), e))
    try:
        dn = bind_dn or lsettings.BIND_DN
        password = bind_password or lsettings.BIND_PASSWORD
        params = dict(server=server)
        if lsettings.USE_SASL:
            params['authentication'] = ldap3.AUTH_SASL
            params['sasl_mechanism'] = 'DIGEST-MD5'
            params['sasl_credentials'] = (dn, password)
        elif dn:
            params['authentication'] = ldap3.AUTH_SIMPLE
            params['user'] = dn
            params['password'] = password
        else:
            params['authentication'] = ldap3.AUTH_ANONYMOUS
        connection = ldap3.Connection(**params)

        if lsettings.START_TLS:
            connection.start_tls()

        if not connection.bind():
            if connection.result.get('description'):
                if 'invalidCredentials' in connection.result['description']:
                    raise Exception(str('Username and password do not match.'))
                raise Exception(connection.result['description'])
            raise Exception('Bind call failed.')
    except Exception as e:
        raise Exception('%s\n%s %s' % (_('Error when trying to authenticate on LDAP server.'), _('Error:'), e))
    else:
        return connection


# ldap_search function
# ----------------------------------------------------------------------------
def ldap_search(base_dn, sfilter, attrs='all', connection=None):
    if not connection:
        connection = get_connection()
    if attrs == 'all':
        attrs = ldap3.ALL_ATTRIBUTES
    # search user lsettings
    try:
        connection.search(base_dn, search_filter=sfilter, attributes=attrs, size_limit=lsettings.SEARCH_LIMIT, time_limit=lsettings.TIEMOUT)
        results = connection.response
    except Exception as e:
        raise Exception('%s\n%s %s\n%s\nBase dn: %s\nFilter: %s\nAttrs: %s' % (
            _('Search on LDAP server failed.'),
            _('Error:'),
            e,
            _('Arguments:'),
            base_dn,
            sfilter,
            attrs,
        ))
    return results


# get_user_info function
# ----------------------------------------------------------------------------
def get_user_info(username, connection=None):
    results = ldap_search(lsettings.USER_SEARCH_SCOPE, lsettings.USER_SEARCH_FILTER % dict(user=username), connection=connection)
    if not results:
        raise Exception(str(_('User not found.')))
    if len(results) > 1:
        logger.warning('Multiple results found in LDAP server for search:\n%s\n%s\n%s', lsettings.USER_SEARCH_SCOPE, 'ldap3.SCOPE_SUBTREE', lsettings.USER_SEARCH_FILTER % dict(user=username))
    return results[0]['dn'], results[0]['attributes']


# authenticate function
# ----------------------------------------------------------------------------
def authenticate(user_dn, password):
    return get_connection(user_dn, password)


# update_user_email function
# ----------------------------------------------------------------------------
def update_user_email(user, user_info):
    if user.id and not lsettings.ALWAYS_UPDATE:
        return
    if lsettings.EMAIL_FIELD and user_info.get(lsettings.EMAIL_FIELD):
        email = user_info[lsettings.EMAIL_FIELD]
        if isinstance(email, (list, tuple)):
            email = email[0]
        if user.email != email:
            user.email = email
            if user.id:
                user.save(update_fields=['email'])


# test_connection function
# ----------------------------------------------------------------------------
def test_ldap_connection(username, password=None):
    try:
        connection = get_connection()
        user_dn, user_info = get_user_info(username, connection)
    except Exception as e:
        return False, '%s %s\n%s' % (_('Error when trying to get user information.'), _('Error:'), e)
    else:
        success = True
        msg = ''
        if password:
            try:
                authenticate(user_dn, password)
            except Exception as e:
                success = False
                msg = '%s\n<br/>%s\n<br/>\n<br/>' % (escape(_('Login failed (however the user exists in LDAP).')), defaultfilters.linebreaksbr(escape(e)))
            else:
                msg = '%s\n<br/>\n<br/>' % escape(_('Login succeeded.'))
        msg += '%s' % escape(_('User "%s" data:') % username)
        for k, v in user_info.items():
            msg += '\n<br/>    <b>%s:</b> %s' % (escape(k), escape(v))
        return success, mark_safe(msg)
