#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
LDAP utility functions
Requires ldap3 > 2.1
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
    USER_LIST_FILTER = '(objectClass=person)'
    GROUP_SEARCH_SCOPE = 'ou=group,dc=server,dc=net'
    GROUP_SEARCH_FILTER = '(gidNumber=%(group)s)'
    GROUP_LIST_FILTER = '(objectClass=posixGroup)'
    ALWAYS_UPDATE = True
    VIRTUAL_ATTRIBUTES = None
    USER_ID_FIELD = 'uid'
    USER_EMAIL_FIELD = 'mail'
    USER_GROUPS_FIELD = 'gidNumber'
    USER_GROUPS_USE_DN = False
    GROUP_MEMBERS_FIELD = 'memberUid'
    GROUP_MEMBERS_USE_DN = False
    START_TLS = False
    TLS_VERSION = None  # ssl.PROTOCOL_SSLv23
    CHECK_CERT = True
    SEARCH_LIMIT = 50000
    CA_CERT = None
    USE_SASL = False
    BIND_DN = ''
    BIND_PASSWORD = ''
    TIMEOUT = 15
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
            if lsettings.TLS_VERSION:
                tls_params['version'] = lsettings.TLS_VERSION
            if lsettings.CA_CERT:
                tls_params['ca_certs_file'] = lsettings.CA_CERT
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
            params['authentication'] = ldap3.SASL
            params['sasl_mechanism'] = 'DIGEST-MD5'
            params['sasl_credentials'] = (dn, password)
        elif dn:
            params['authentication'] = ldap3.SIMPLE
            params['user'] = dn
            params['password'] = password
        else:
            params['authentication'] = ldap3.ANONYMOUS
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
        attrs = [ldap3.ALL_ATTRIBUTES]
        if lsettings.VIRTUAL_ATTRIBUTES:
            attrs.extend(lsettings.VIRTUAL_ATTRIBUTES.split(','))
    # search user lsettings
    try:
        connection.search(base_dn, search_filter=sfilter, attributes=attrs, size_limit=lsettings.SEARCH_LIMIT, time_limit=lsettings.TIMEOUT)
        results = list()
        for r in connection.response:
            decoded_attrs = dict()
            for key, values in r['raw_attributes'].items():
                if values:
                    decoded_attrs[key] = [v.decode('utf-8', 'replace') for v in values]
            results.append(dict(dn=r['dn'], attributes=decoded_attrs, raw_attributes=r['raw_attributes']))
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


# get_all_users function
# ----------------------------------------------------------------------------
def get_all_users(connection=None):
    users = dict()
    results = ldap_search(lsettings.USER_SEARCH_SCOPE, lsettings.USER_LIST_FILTER, connection=connection)
    for user in results:
        users[user['dn']] = user['attributes']
    return users


# get_all_groups function
# ----------------------------------------------------------------------------
def get_all_groups(connection=None):
    groups = dict()
    results = ldap_search(lsettings.GROUP_SEARCH_SCOPE, lsettings.GROUP_LIST_FILTER, connection=connection)
    for group in results:
        groups[group['dn']] = group['attributes']
    return groups


# get_user_info function
# ----------------------------------------------------------------------------
def get_user_info(username, connection=None):
    results = ldap_search(lsettings.USER_SEARCH_SCOPE, lsettings.USER_SEARCH_FILTER % dict(user=username), connection=connection)
    if not results:
        raise Exception(str(_('User not found.')))
    if len(results) > 1:
        logger.warning('Multiple results found in LDAP server for search:\n%s\n%s\n%s', lsettings.USER_SEARCH_SCOPE, 'ldap3.SUBTREE', lsettings.USER_SEARCH_FILTER % dict(user=username))
    return results[0]['dn'], results[0]['attributes']


# get_user_groups function
# ----------------------------------------------------------------------------
def get_user_groups(user_dn, user_attrs, connection=None):
    if not connection:
        connection = get_connection()
    groups = dict()
    # get groups referred by group objects
    if lsettings.GROUP_MEMBERS_FIELD:
        if lsettings.GROUP_MEMBERS_USE_DN:
            search_filter = '(%s=%s)' % (lsettings.GROUP_MEMBERS_FIELD, user_dn)
        elif hasattr(user_attrs, 'items') and user_attrs.get(lsettings.USER_ID_FIELD):
            search_filter = '(%s=%s)' % (lsettings.GROUP_MEMBERS_FIELD, user_attrs[lsettings.USER_ID_FIELD][0])
        else:
            search_filter = None
        if search_filter:
            results = ldap_search(lsettings.GROUP_SEARCH_SCOPE, search_filter, connection=connection)
            for group in results:
                groups[group['dn']] = group['attributes']
    # get groups referred by user object
    if lsettings.USER_GROUPS_FIELD and hasattr(user_attrs, 'items') and user_attrs.get(lsettings.USER_GROUPS_FIELD):
        for name in user_attrs[lsettings.USER_GROUPS_FIELD]:
            if lsettings.USER_GROUPS_USE_DN:
                results = ldap_search(name, lsettings.GROUP_LIST_FILTER, connection=connection)
            else:
                results = ldap_search(lsettings.GROUP_SEARCH_SCOPE, lsettings.GROUP_SEARCH_FILTER % dict(group=name), connection=connection)
            for group in results:
                if group['dn'] not in groups:
                    groups[group['dn']] = group['attributes']
    return groups


# authenticate function
# ----------------------------------------------------------------------------
def authenticate(user_dn, password):
    return get_connection(user_dn, password)


# update_user_email function
# ----------------------------------------------------------------------------
def update_user_email(user, user_info, unique=False):
    if user.id and not lsettings.ALWAYS_UPDATE:
        return
    if lsettings.USER_EMAIL_FIELD and user_info.get(lsettings.USER_EMAIL_FIELD):
        email = user_info[lsettings.USER_EMAIL_FIELD]
        if isinstance(email, (list, tuple)):
            email = email[0]
        if user.email != email:
            if unique:
                suffix = 0
                user_query = user.__class__.objects.exclude(id=user.id) if user.id else user.__class__.objects.all()
                while user_query.filter(email=email).exists():
                    to_rep = '+%s@' % suffix if suffix else '@'
                    email = email.replace(to_rep, '+%s@' % suffix)
                    suffix += 1
            user.email = email
            if user.id:
                user.save(update_fields=['email'])


# test_connection function
# ----------------------------------------------------------------------------
def test_ldap_connection(username, password=None, get_groups=False):
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
        msg += '%s<ul>' % escape(_('User "%s" data:') % username)
        for k, v in user_info.items():
            msg += '\n<li><b>%s:</b> %s</li>' % (escape(k), escape(v))
        msg += '\n</ul>'
        if get_groups and user_info:
            msg += '\n<br/>%s\n<br/>' % escape(_('User groups:'))
            try:
                groups = get_user_groups(user_dn, user_info, connection=connection)
            except Exception as e:
                msg += '%s\n<br/>%s\n<br/>' % (escape(_('Error when trying to get groups.')), e)
            else:
                gids = list(groups.keys())
                if gids:
                    gids.sort()
                    for gid in gids:
                        msg += '\n<br/><b>%s</b><ul>' % escape(gid)
                        for k, v in groups[gid].items():
                            msg += '\n<li><b>%s:</b> %s</li>' % (escape(k), escape(v))
                        msg += '\n</ul>'
                else:
                    msg += '%s' % (escape(_('No groups found.')))
        return success, mark_safe(msg)
