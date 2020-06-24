#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
LDAP utility functions
Requires ldap3 > 2.1
'''
from ldap3.utils.conv import escape_filter_chars
import ldap3
import logging
import ssl
# Django
from django.conf import settings
from django.template import defaultfilters
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('djwutils.ldap_utils')


# LDAP default settings object
class LDAPDefaultSettings(object):
    SETTINGS_PREFIX = 'AUTH_LDAP_'
    SERVER_URI = 'ldap://server.net'
    USER_SEARCH_SCOPE = 'ou=People,dc=server,dc=net'
    USER_SEARCH_FILTER = '(objectClass=person)'
    GROUP_SEARCH_SCOPE = 'ou=group,dc=server,dc=net'
    GROUP_SEARCH_FILTER = '(objectClass=posixGroup)'
    ALWAYS_UPDATE = True
    VIRTUAL_ATTRIBUTES = None
    USER_ID_FIELD = 'uid'
    USER_EMAIL_FIELD = 'mail'
    USER_GROUPS_FIELD = 'gidNumber'
    USER_GROUPS_USE_DN = False
    GROUP_ID_FIELD = 'gidNumber'
    GROUP_NAME_FIELD = 'cn'
    GROUP_MEMBERS_FIELD = 'memberUid'
    GROUP_MEMBERS_USE_DN = False
    GROUP_SUB_GROUPS_FIELD = None
    GROUP_SUB_GROUPS_USE_DN = False
    START_TLS = False
    TLS_VERSION = None  # ssl.PROTOCOL_TLSv1_2
    CHECK_CERT = True
    CA_CERT = None
    USE_SASL = False
    BIND_DN = ''
    BIND_PASSWORD = ''
    PAGE_SIZE = 1000
    TIMEOUT = 15


def get_conf(key):
    return getattr(settings, LDAPDefaultSettings.SETTINGS_PREFIX + key, getattr(LDAPDefaultSettings, key))


# get_connection function
# ----------------------------------------------------------------------------
def get_connection(bind_dn=None, bind_password=None):
    try:
        sv_params = dict(host=get_conf('SERVER_URI'), use_ssl=get_conf('SERVER_URI').startswith('ldaps://'))
        if get_conf('START_TLS'):
            tls_params = dict()
            if get_conf('CHECK_CERT'):
                tls_params = dict(validate=ssl.CERT_REQUIRED)
            else:
                tls_params = dict(validate=ssl.CERT_NONE)
            if get_conf('TLS_VERSION'):
                tls_params['version'] = get_conf('TLS_VERSION')
            if get_conf('CA_CERT'):
                tls_params['ca_certs_file'] = get_conf('CA_CERT')
            tls = ldap3.Tls(**tls_params)
            sv_params['tls'] = tls
            sv_params['use_ssl'] = True
        server = ldap3.Server(**sv_params)
    except Exception as e:
        raise Exception('%s\n%s %s' % (_('Error when initializing connection with LDAP server.'), _('Error:'), e))
    try:
        dn = bind_dn or get_conf('BIND_DN')
        password = bind_password or get_conf('BIND_PASSWORD')
        params = dict(server=server)
        if get_conf('USE_SASL'):
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

        if get_conf('START_TLS'):
            connection.open()
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
        if get_conf('VIRTUAL_ATTRIBUTES'):
            attrs.extend(get_conf('VIRTUAL_ATTRIBUTES').split(','))
    try:
        entry_generator = connection.extend.standard.paged_search(base_dn, search_filter=sfilter, attributes=attrs, paged_size=get_conf('PAGE_SIZE'), time_limit=get_conf('TIMEOUT'), generator=True)
        results = list()
        for entry in entry_generator:
            if 'dn' in entry and 'raw_attributes' in entry:
                decoded_attrs = dict()
                for key, values in entry['raw_attributes'].items():
                    if values:
                        decoded_attrs[key] = [v.decode('utf-8', 'replace') for v in values]
                results.append(dict(dn=entry['dn'], attributes=decoded_attrs, raw_attributes=entry['raw_attributes']))
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
    results = ldap_search(get_conf('USER_SEARCH_SCOPE'), get_conf('USER_SEARCH_FILTER'), connection=connection)
    for user in results:
        users[user['dn']] = user['attributes']
    return users


# get_all_groups function
# ----------------------------------------------------------------------------
def get_all_groups(connection=None):
    groups = dict()
    results = ldap_search(get_conf('GROUP_SEARCH_SCOPE'), get_conf('GROUP_SEARCH_FILTER'), connection=connection)
    for group in results:
        groups[group['dn']] = group['attributes']
    return groups


# get_user_info function
# ----------------------------------------------------------------------------
def get_user_info(username, connection=None):
    l_filter = '(&%s(%s=%s))' % (get_conf('USER_SEARCH_FILTER'), get_conf('USER_ID_FIELD'), escape_filter_chars(username))
    results = ldap_search(get_conf('USER_SEARCH_SCOPE'), l_filter, connection=connection)
    if not results:
        raise Exception(str(_('User not found.')))
    if len(results) > 1:
        logger.warning('Multiple results found in LDAP server for search:\n%s\n%s\n%s', get_conf('USER_SEARCH_SCOPE'), 'ldap3.SUBTREE', l_filter)
    return results[0]['dn'], results[0]['attributes']


# get_group_info function
# ----------------------------------------------------------------------------
def get_group_info(group_uid, connection=None):
    l_filter = '(&%s(%s=%s))' % (get_conf('GROUP_SEARCH_FILTER'), get_conf('GROUP_ID_FIELD'), escape_filter_chars(group_uid))
    results = ldap_search(get_conf('GROUP_SEARCH_SCOPE'), l_filter, connection=connection)
    if not results:
        raise Exception(str(_('Group not found.')))
    if len(results) > 1:
        logger.warning('Multiple results found in LDAP server for search:\n%s\n%s\n%s', get_conf('GROUP_SEARCH_SCOPE'), 'ldap3.SUBTREE', l_filter)
    return results[0]['dn'], results[0]['attributes']


# get_group_sub_groups function
# ----------------------------------------------------------------------------
def get_group_sub_groups(group_dn, group_attrs, level=1, connection=None):
    sub_groups = list()
    if get_conf('GROUP_SUB_GROUPS_FIELD') and (get_conf('GROUP_SUB_GROUPS_USE_DN') or get_conf('GROUP_ID_FIELD')) and hasattr(group_attrs, 'items') and group_attrs.get(get_conf('GROUP_SUB_GROUPS_FIELD')):
        for ref in group_attrs[get_conf('GROUP_SUB_GROUPS_FIELD')]:
            if not ref:
                continue
            if get_conf('GROUP_SUB_GROUPS_USE_DN'):
                if ref == group_dn:
                    continue  # avoid infinite group loops
                if '=' not in ref:
                    continue  # value is not a valid dn
                results = ldap_search(ref, get_conf('GROUP_SEARCH_FILTER'), connection=connection)
            else:
                results = ldap_search(get_conf('GROUP_SEARCH_SCOPE'), '(&%s(%s=%s))' % (get_conf('GROUP_SEARCH_FILTER'), get_conf('GROUP_ID_FIELD'), escape_filter_chars(ref)), connection=connection)
            for sub_group in results:
                if sub_group['dn'] == group_dn:
                    continue  # avoid infinite group loops
                sub_groups.append(sub_group)
                sub_group_attrs = sub_group['attributes'] if hasattr(sub_group['attributes'], 'items') else dict()
                sub_group_attrs['_sub_group_level'] = [level]
                sub_groups.extend(get_group_sub_groups(sub_group['dn'], sub_group_attrs, level=level + 1, connection=connection))
    return sub_groups


# get_user_groups function
# ----------------------------------------------------------------------------
def get_user_groups(user_dn, user_attrs, connection=None):
    if not connection:
        connection = get_connection()
    groups = dict()
    # get groups referred by group objects
    if get_conf('GROUP_MEMBERS_FIELD'):
        if get_conf('GROUP_MEMBERS_USE_DN'):
            search_filter = '(&%s(%s=%s))' % (get_conf('GROUP_SEARCH_FILTER'), get_conf('GROUP_MEMBERS_FIELD'), escape_filter_chars(user_dn))
        elif get_conf('USER_ID_FIELD') and hasattr(user_attrs, 'items') and user_attrs.get(get_conf('USER_ID_FIELD')):
            search_filter = '(&%s(%s=%s))' % (get_conf('GROUP_SEARCH_FILTER'), get_conf('GROUP_MEMBERS_FIELD'), escape_filter_chars(user_attrs[get_conf('USER_ID_FIELD')][0]))
        else:
            search_filter = None
        if search_filter:
            results = ldap_search(get_conf('GROUP_SEARCH_SCOPE'), search_filter, connection=connection)
            for group in results:
                groups[group['dn']] = group['attributes']
                for sub_group in get_group_sub_groups(group['dn'], group['attributes'], connection=connection):
                    groups[sub_group['dn']] = sub_group['attributes']
    # get groups referred by user object
    if get_conf('USER_GROUPS_FIELD') and hasattr(user_attrs, 'items') and user_attrs.get(get_conf('USER_GROUPS_FIELD')):
        for name in user_attrs[get_conf('USER_GROUPS_FIELD')]:
            if get_conf('USER_GROUPS_USE_DN'):
                results = ldap_search(name, get_conf('GROUP_SEARCH_FILTER'), connection=connection)
            else:
                search_filter = '(&%s(%s=%s))' % (get_conf('GROUP_SEARCH_FILTER'), get_conf('GROUP_ID_FIELD'), escape_filter_chars(name))
                results = ldap_search(get_conf('GROUP_SEARCH_SCOPE'), search_filter, connection=connection)
            for group in results:
                if group['dn'] not in groups:
                    groups[group['dn']] = group['attributes']
                    for sub_group in get_group_sub_groups(group['dn'], group['attributes'], connection=connection):
                        groups[sub_group['dn']] = sub_group['attributes']
    return groups


# authenticate function
# ----------------------------------------------------------------------------
def authenticate(user_dn, password):
    return get_connection(user_dn, password)


# update_user_email function
# ----------------------------------------------------------------------------
def update_user_email(user, user_info, unique=False):
    if user.id and not get_conf('ALWAYS_UPDATE'):
        return
    if get_conf('USER_EMAIL_FIELD') and user_info.get(get_conf('USER_EMAIL_FIELD')):
        email = user_info[get_conf('USER_EMAIL_FIELD')]
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
        for k, v in sorted(user_info.items()):
            msg += '\n<li><b>%s:</b> %s</li>' % (escape(k), escape(v))
        msg += '\n</ul>'
        if get_groups and user_info:
            msg += '\n<br/>%s\n<br/>' % escape(_('User groups:'))
            try:
                groups = get_user_groups(user_dn, user_info, connection=connection)
            except Exception as e:
                success = False
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
