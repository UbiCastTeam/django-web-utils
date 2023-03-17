"""
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
"""
import datetime
import logging
import os
import socket
import sys
import traceback
# Django
from django.conf import settings
from django.core import mail
from django.db.models.query import QuerySet
from django.template import Context, Engine
from django.utils import translation
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
# utils
from django_web_utils import html_utils
from django_web_utils.logging_utils import IgnoreTimeoutErrors, IgnoreDatabaseErrors

logger = logging.getLogger('djwutils.emails_utils')


def _get_context():
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
        ctx = ctx_processor()
        if ctx and not isinstance(ctx, dict):
            logger.error('Emails context processor returned an invalid object for context (must be a dict): %s', ctx)
            ctx = None
    if (not ctx or not ctx.get('sender')) and getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        if not ctx:
            ctx = dict()
        ctx['sender'] = settings.DEFAULT_FROM_EMAIL
    return ctx


def _get_recipients_list(recipients):
    if not recipients:
        # Send emails to managers if no email is given
        recipients = [a[1] for a in settings.MANAGERS]
    elif isinstance(recipients, dict):
        # Convert dict to list
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


def send_template_emails(template, context=None, recipients=None, content_subtype='html', attachments=None):
    """
    Function to send emails with a template.
    Arguments:
        template: template path.
        context: can be a dict or None.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en'}}
            list format: [{'email': 'test@test.com', 'lang': 'en'}]
            str format: test@test.com
            (user objects can be given as recipient)
        content_subtype: email content type.
        attachments: list of attachments.
    """
    # Get common context
    common_ctx = _get_context()
    if common_ctx:
        base_ctx = dict(common_ctx)
    else:
        base_ctx = dict()
    if context:
        base_ctx.update(context)
    # Get sender
    sender = base_ctx['sender'] if base_ctx.get('sender') else '"Default sender name" <sender@address.com>'
    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = _get_recipients_list(recipients)
    if not cleaned_rcpts:
        msg = 'No emails have been sent: no valid recipients given.'
        logger.error('%s Recipients: %s.', msg, recipients)
        return False, msg
    # Get template
    engine = Engine.get_default()
    if template.startswith('/'):
        with open(template, 'r') as file_obj:
            template = file_obj.read()
        tplt = engine.from_string(template)
    else:
        tplt = engine.get_template(template)
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
            lang = recipient.get('lang')
        else:
            # User object
            address = getattr(recipient, 'email')
            name = recipient.get_full_name()
            lang = getattr(recipient, 'emails_lang', None)
        if address.count('@') != 1:
            logger.error('Recipient ignored because his email address is invalid: %s', address)
            error = 'invalid address'
            continue
        if name:
            name = name.replace('"', '”').replace('\'', '’')
        # Activate correct lang
        if not lang:
            lang = base_ctx.get('lang')
            if not lang:
                lang = settings.LANGUAGE_CODE[:2]
                if not lang:
                    lang = 'en'
        if lang != last_lang:
            last_lang = lang
            translation.activate(lang)
        # Get subject and content
        ctx = dict(base_ctx)
        ctx['recipient'] = recipient
        ctx['LANGUAGE_CODE'] = lang
        content = tplt.render(Context(ctx))
        subject_start = content.index('<subject>') + 9
        subject_end = subject_start + content[subject_start:].index('</subject>')
        subject = content[subject_start:subject_end].replace('\r', '').replace('\n', ' ').strip()
        content = content[:subject_start - 9] + content[subject_end + 10:]
        # Prepare email
        address_with_name = address if not name else '"%s" <%s>' % (name, address)
        msg = mail.EmailMessage(subject, content, sender, [address_with_name])
        if attachments:
            for attachment in attachments:
                msg.attach_file(attachment)
        msg.content_subtype = content_subtype  # by default, set email content type to html
        # Send email
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


def send_emails(subject, content, recipients=None, content_subtype='html', attachments=None):
    """
    Function to send emails without template.
    Arguments:
        subject: email subject.
        content: email content.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en'}}
            list format: [{'email': 'test@test.com', 'lang': 'en'}]
            str format: test@test.com
            (user objects can be given as recipient)
        content_subtype: email content type.
        attachments: list of attachments.
    """
    # Get common context
    ctx = _get_context()
    # Get sender
    sender = ctx['sender'] if ctx.get('sender') else '"Default sender name" <sender@address.com>'
    # Clean recipients list (get a list of User model or dict with at least email in keys)
    cleaned_rcpts = _get_recipients_list(recipients)
    if not cleaned_rcpts:
        msg = 'No emails have been sent: no valid recipients given.'
        logger.error('%s Recipients: %s.', msg, recipients)
        return False, msg
    # Prepare emails messages
    subject = subject.replace('\r', '').replace('\n', ' ').strip()
    connection = None
    sent = list()
    error = 'no recipient'
    for recipient in cleaned_rcpts:
        # Get recipient address and lang
        if isinstance(recipient, dict):
            address = recipient.get('email', '')
            name = recipient.get('name', '')
        else:
            # User object
            address = getattr(recipient, 'email')
            name = recipient.get_full_name()
        if address.count('@') != 1:
            logger.error('Recipient ignored because his email address is invalid: %s', address)
            error = 'invalid address'
            continue
        if name:
            name = name.replace('"', '”').replace('\'', '’')
        # Prepare email
        address_with_name = address if not name else '"%s" <%s>' % (name, address)
        msg = mail.EmailMessage(subject, content, sender, [address_with_name])
        if attachments:
            for attachment in attachments:
                msg.attach_file(attachment)
        msg.content_subtype = content_subtype  # by default, set email content type to html
        # Send email
        try:
            if not connection:
                connection = mail.get_connection()
            connection.send_messages([msg])
        except Exception as e:
            error = e
            logger.error('Error when trying to send email to: %s.\n%s' % (address, traceback.format_exc()))
        else:
            sent.append(address)
            logger.info('Email with subject "%s" sent to "%s".', subject, address)
    if not sent:
        return False, 'No emails have been sent. Last error when trying to send email: %s' % error
    return True, sent


def send_error_report_emails(title=None, error=None, recipients=None, filter_error=True, show_traceback=True):
    """
    Function to send last error traceback.
    Arguments:
        title: label to add to subject.
        error: can be a dict or None.
        recipients: can be a dict, a list, a str or None.
            dict format: {'test@test.com': {'lang': 'en'}}
            list format: [{'email': 'test@test.com', 'lang': 'en'}]
            str format: test@test.com
            (user objects can be given as recipient)
        filter_error: filter error type with default filters.
    """
    if title:
        title = 'Error report - %s' % title
    else:
        title = 'Error report'

    no_sending_msg = None
    if settings.DEBUG:
        no_sending_msg = 'Error report will not be sent because the debug mode is enabled.'
    elif filter_error:
        # Check that last error is passing filters
        class Record:
            exc_info = sys.exc_info()
        if Record.exc_info[0] is not None:
            filters = (IgnoreTimeoutErrors(), IgnoreDatabaseErrors())
            for ft in filters:
                if not ft.filter(Record):
                    no_sending_msg = 'Error report will not be sent because the error is matching an exclusion filter.'
                    break

    if no_sending_msg:
        logger.info('%s\nSubject: %s\nTo: %s\nContent:\n%s\n%s', no_sending_msg, title, recipients, error, traceback.format_exc())
        return True, no_sending_msg

    fieldset_style = 'style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;"'
    content = '<div style="margin-bottom: 8px;">Message sent at: %s<br/>\nUnix user: %s<br/>\nSystem hostname: %s</div>' % (
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), conditional_escape(os.environ.get('USER')), conditional_escape(socket.gethostname())
    )
    # Error information
    if error:
        content += '<fieldset %s>\n' % fieldset_style
        content += '<legend><b> Error </b></legend>\n'
        content += '<div>%s</div>\n' % conditional_escape(error).replace('\n', '<br/>\n')
        content += '</fieldset>\n\n'
    # Traceback information
    if show_traceback:
        content += '<fieldset %s>\n' % fieldset_style
        content += '<legend><b> Traceback </b></legend>\n'
        content += '<div>%s</div>\n' % html_utils.get_html_traceback()
        content += '</fieldset>\n\n'
    # Send emails
    content = mark_safe(content)
    tplt = getattr(settings, 'EMAIL_ERROR_TEMPLATE', None)
    if tplt:
        return send_template_emails(tplt, dict(
            title=title,
            error=error,
            content=content,
        ), recipients=recipients)
    else:
        return send_emails(title, content, recipients)
