#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Emails utility functions

Optional settings:
    - EMAIL_CONTEXT_PROCESSOR:
        This var should point to a function. The object returned by the
        function must be a dict and should contain a valid sender field
        (something like '"name" <sender@address.com>').
    - EMAIL_ERROR_TEMPLATE:
        The template to use to prepare error report emails.

The template should contain a subject tag.
For example, a valid template could look like this:
<subject>The email subject</subject>
The email content
'''
import datetime
import traceback
import logging
logger = logging.getLogger('djwutils.emails_utils')
# Django
from django.conf import settings
from django.core import mail
from django.db.models.query import QuerySet
from django.template import Context
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
# utils
from . import html_utils


# get context
# ----------------------------------------------------------------------------
def _get_context(request=None):
    if '_context_processor' not in globals():
        # Get context fct
        ctx_processor = None
        if getattr(settings, 'EMAIL_CONTEXT_PROCESSOR', None):
            ctx_processor = settings.EMAIL_CONTEXT_PROCESSOR
            try:
                module_name = ctx_processor.split('.')[-1]
                module_path = ctx_processor[:-len(module_name) - 1]
                if not module_path:
                    module_path = '.'
                ctx_processor = __import__(module_path, fromlist=[module_name])
                ctx_processor = getattr(ctx_processor, module_name)
            except Exception as e:
                logger.error('Failed to import emails context processor: %s', e)
            else:
                if not hasattr(ctx_processor, '__call__'):
                    ctx_processor = None
        globals()['_context_processor'] = ctx_processor
    else:
        ctx_processor = globals()['_context_processor']
    if not ctx_processor:
        ctx = None
    else:
        ctx = ctx_processor(request)
        if ctx and not isinstance(ctx, dict):
            logger.error('Emails context processor returned an invalid object for context (must be a dict): %s', ctx)
            ctx = None
    if (not ctx or not ctx.get('sender')) and getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        if not ctx:
            ctx = dict()
        ctx['sender'] = settings.DEFAULT_FROM_EMAIL
    return ctx


# get recipients list
# ----------------------------------------------------------------------------
def _get_recipients_list(recipients, context=None):
    # Search for recipients
    if not recipients:
        recipients = context.get('recipients')
        if not recipients:
            recipients = context.get('recipient')
            if not recipients:
                # Send emails to managers if no email is given
                recipients = [a[1] for a in settings.MANAGERS]
    if isinstance(recipients, dict):
        as_list = list()
        for key, value in recipients.items():
            if isinstance(value, dict):
                value['email'] = key
                as_list.append(value)
            elif hasattr(value, 'email'):
                # User model
                as_list.append(value)
            else:
                as_list.append(dict(email=key, info=value))
        recipients = as_list
    elif not isinstance(recipients, (tuple, list, QuerySet)):
        recipients = [recipients]
    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = list()
    for recipient in recipients:
        if isinstance(recipient, str):
            cleaned_rcpts.append(dict(email=recipient))
        elif isinstance(recipient, dict):
            if recipient.get('email'):
                cleaned_rcpts.append(recipient)
        elif getattr(recipient, 'email', ''):
            cleaned_rcpts.append(recipient)
    return cleaned_rcpts


# send_template_emails (to send emails with a template)
# ----------------------------------------------------------------------------
def send_template_emails(template, context=None, recipients=None, request=None, content_subtype='html'):
    '''
    Function to send emails with a template.
    Arguments:
        context: can be a dict or None.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en'}}
            list format: [{'email': 'test@test.com', 'lang': 'en'}]
            str format: test@test.com
            (user objects can be given as recipient)
        request: is given to context processor.
    '''
    # Get common context
    common_ctx = _get_context(request)
    if common_ctx:
        base_ctx = dict(common_ctx)
    else:
        base_ctx = dict()
    if context:
        base_ctx.update(context)
    # Get sender
    sender = base_ctx['sender'] if base_ctx.get('sender') else '"Default sender name" <sender@address.com>'
    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = _get_recipients_list(recipients, context)
    if not cleaned_rcpts:
        msg = 'No emails have been sent: no valid recipients given.'
        logger.error('%s\nEmail context: %s', msg, base_ctx)
        return False, msg
    # Prepare emails messages
    connection = None
    sent = list()
    error = 'unknown'
    cur_lang = translation.get_language()
    last_lang = cur_lang
    for recipient in cleaned_rcpts:
        # Get recipient address and lang
        if isinstance(recipient, dict):
            address = recipient.get('email', '')
            name = recipient.get('name', '')
            lang = recipient.get('lang', 'en')
        else:
            # User object
            address = getattr(recipient, 'email')
            name = recipient.get_full_name()
            lang = getattr(recipient, 'emails_lang', None)
        if '@' not in address:
            logger.error('Recipient ignored because his email address is invalid: %s', address)
            error = 'invalid address'
            continue
        if name:
            name = name.replace('"', '”').replace('\'', '’')
        # Activate correct lang
        if not lang:
            lang = 'en'
        if lang != last_lang:
            last_lang = lang
            translation.activate(lang)
        # Get subject and content
        ctx = dict(base_ctx)
        ctx['recipient'] = recipient
        content = render_to_string(template, ctx, Context(dict(LANGUAGE_CODE=lang)))
        subject_start = content.index('<subject>') + 9
        subject_end = subject_start + content[subject_start:].index('</subject>')
        subject = content[subject_start:subject_end].strip()
        content = content[:subject_start - 9] + content[subject_end + 10:]
        # Send email
        address_with_name = address if not name else '"%s" <%s>' % (name, address)
        msg = mail.EmailMessage(subject, content, sender, [address_with_name])
        msg.content_subtype = content_subtype  # by default, set email content type to html
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception as e:
            error = e
            logger.error('Error when trying to send email to: %s.\n%s' % (address, traceback.format_exc()))
        else:
            sent.append(address)
            logger.info('Email with subject "%s" sent to "%s" (tplt).', subject, address)
    if last_lang != cur_lang:
        translation.activate(cur_lang)
    if not sent:
        return False, 'No emails have been sent. Last error when trying to send email: %s' % error
    return True, sent


# send_emails (to send emails without template)
# ----------------------------------------------------------------------------
def send_emails(subject, content, recipients=None, request=None, content_subtype='html'):
    # Get common context
    ctx = _get_context(request)
    # Get sender
    sender = ctx['sender'] if ctx.get('sender') else '"Default sender name" <sender@address.com>'
    # Get recipients
    if not recipients:
        # Send emails to managers if no email is given
        recipients = [a[1] for a in settings.MANAGERS]
    elif isinstance(recipients, dict):
        recipients = list(recipients.keys())
    elif not isinstance(recipients, (tuple, list)):
        recipients = [recipients]
    # Prepare emails messages
    connection = None
    sent = list()
    error = 'no recipient'
    for recipient in recipients:
        msg = mail.EmailMessage(subject, content, sender, [recipient])
        msg.content_subtype = content_subtype  # by default, set email content type to html
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception as e:
            error = e
            logger.error('Error when trying to send email to: %s.\n%s' % (recipient, traceback.format_exc()))
        else:
            sent.append(recipient[recipient.index('<') + 1:].rstrip('> ') if '<' in recipient else recipient)
            logger.info('Email with subject "%s" sent to "%s".', subject, recipient)
    if not sent:
        return False, 'No emails have been sent. Last error when trying to send email: %s' % error
    return True, sent


# send_error_report_emails (to send last traceback)
# ----------------------------------------------------------------------------
def send_error_report_emails(title=None, error=None, recipients=None, request=None):
    if request:
        title = ' (%s)' % title if title else ''
        title = 'Error at %s%s' % (request.get_full_path(), title)
    elif title:
        title = 'Error report - %s' % title
    else:
        title = 'Error report'
    
    fieldset_style = 'style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;"'
    content = '<div style="margin-bottom: 8px;">Message sent at: %s</div>' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Error information
    if error:
        content += '<fieldset %s>\n' % fieldset_style
        content += '<legend><b> Error </b></legend>\n'
        content += '<div>%s</div>\n' % conditional_escape(error).replace('\n', '<br/>\n')
        content += '</fieldset>\n\n'
    # Traceback information
    content += '<fieldset %s>\n' % fieldset_style
    content += '<legend><b> Traceback </b></legend>\n'
    content += '<div style="color: #800;">%s</div>\n' % html_utils.get_html_traceback()
    content += '</fieldset>\n\n'
    # Request's info
    if request:
        left_col_style = 'vertical-align: top; color: #666; padding-right: 8px; text-align: right;'
        right_col_style = 'vertical-align: top;'
        # Main request's info
        content += '<fieldset %s>\n' % fieldset_style
        content += '<legend><b> Main request\'s info </b></legend>\n'
        content += '<table>\n'
        content += '<tr> <td style="%s"><b>HTTP_USER_AGENT</b></td>\n' % left_col_style
        content += '     <td style="%s"><b>%s</b></td> </tr>\n' % (right_col_style, conditional_escape(request.META.get('HTTP_USER_AGENT', 'unknown')))
        content += '<tr> <td style="%s"><b>REMOTE_ADDR</b></td>\n' % left_col_style
        content += '     <td style="%s"><b>%s</b></td> </tr>\n' % (right_col_style, conditional_escape(request.META.get('REMOTE_ADDR', 'unknown')))
        content += '</table>\n'
        content += '</fieldset>\n\n'
        # Other request's info
        content += '<fieldset %s>\n' % fieldset_style
        content += '<legend><b> Other request\'s info </b></legend>\n'
        content += '<table>\n'
        keys = list(request.META.keys())
        keys.sort()
        for key in keys:
            if key not in ('HTTP_USER_AGENT', 'REMOTE_ADDR'):
                content += '<tr> <td style="%s">%s</td>\n' % (left_col_style, conditional_escape(key))
                content += '     <td style="%s">%s</td> </tr>\n' % (right_col_style, conditional_escape(request.META[key]))
        content += '</table>\n'
        content += '</fieldset>\n'
    content = mark_safe(content)
    # Send emails
    tplt = getattr(settings, 'EMAIL_ERROR_TEMPLATE', None)
    if tplt:
        return send_template_emails(tplt, dict(
            title=title,
            error=error,
            content=content,
        ), recipients=recipients, request=request)
    else:
        return send_emails(title, content, recipients, request)
