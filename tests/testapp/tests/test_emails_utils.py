import re

import pytest
from django.contrib.auth.models import User
from django.core import mail as dj_mail

from django_web_utils import emails_utils

import testapp

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def reset_context_processor():
    if hasattr(emails_utils, '_context_processor'):
        del emails_utils._context_processor


def test_recipients__managers(settings):
    success, sent = emails_utils.send_emails(subject='Test', content='Body')
    assert success is True
    assert sent == [settings.MANAGERS[0][1]]
    assert [m.to[0] for m in dj_mail.outbox] == [settings.MANAGERS[0][1]]


@pytest.mark.parametrize('recipients', [
    pytest.param('test@test.com', id='str'),
    pytest.param(['test@test.com'], id='str as list'),
    pytest.param({'test@test.com': 'data'}, id='dict with str data'),
    pytest.param({'test@test.com': {}}, id='dict with data dict'),
    pytest.param({'test@test.com': User(email='test@test.com')}, id='dict with user'),
    pytest.param([{'email': 'test@test.com'}], id='dict as list'),
    pytest.param(User(email='test@test.com'), id='user'),
    pytest.param([User(email='test@test.com')], id='user as list'),
])
def test_recipients(recipients):
    success, sent = emails_utils.send_emails(subject='Test', content='Body', recipients=recipients)
    assert success is True
    assert sent == ['test@test.com']
    assert [m.to[0] for m in dj_mail.outbox] == ['test@test.com']


def test_no_recipients(settings):
    success, sent = emails_utils.send_emails(subject='Test', content='Body', recipients=[])
    assert success is False
    assert sent == 'No emails have been sent: no valid recipients given.'


@pytest.mark.parametrize('with_context_processor', [
    pytest.param(True, id='with context processor'),
    pytest.param(False, id='no context processor'),
])
def test_send_template_emails(settings, with_context_processor):
    if with_context_processor:
        settings.EMAIL_CONTEXT_PROCESSOR = 'testapp.context.emails_context_processor'
        footer = 'Using context processor'
    else:
        footer = 'No footer'

    recipients = [{'email': 'test@test.com', 'lang': 'fr'}]
    success, sent = emails_utils.send_template_emails('emails/email_test.html', {
        'subject': 'The subject',
        'body': 'The body',
    }, recipients=recipients)
    assert success is True
    assert sent == ['test@test.com']
    assert [m.to[0] for m in dj_mail.outbox] == ['test@test.com']
    assert dj_mail.outbox[0].subject == 'The subject'
    assert dj_mail.outbox[0].body == f'\n<div>The body</div>\n<div><i>{footer}</i></div>\n'


def test_send_template_emails__absolute_path(settings):
    tplt_path = testapp.__path__[0] + '/templates/emails/email_test.html'
    recipients = [{'email': 'test@test.com', 'lang': 'fr'}]
    success, sent = emails_utils.send_template_emails(tplt_path, {
        'subject': 'The subject',
        'body': 'The body',
    }, recipients=recipients)
    assert success is True
    assert sent == ['test@test.com']
    assert [m.to[0] for m in dj_mail.outbox] == ['test@test.com']
    assert dj_mail.outbox[0].subject == 'The subject'
    assert dj_mail.outbox[0].body == '\n<div>The body</div>\n<div><i>No footer</i></div>\n'


def test_send_template_emails__no_recipients(settings):
    success, sent = emails_utils.send_template_emails('emails/email_test.html', {}, recipients=[])
    assert success is False
    assert sent == 'No emails have been sent: no valid recipients given.'


def test_send_template_emails__invalid_context(settings):
    settings.EMAIL_CONTEXT_PROCESSOR = 'does.not.exist'

    recipients = [{'email': 'test@test.com', 'lang': 'fr'}]
    with pytest.raises(RuntimeError):
        emails_utils.send_template_emails('emails/email_test.html', {
            'subject': 'The subject',
            'body': 'The body',
        }, recipients=recipients)
    assert [m.to[0] for m in dj_mail.outbox] == []


@pytest.mark.parametrize('fct, kwargs', [
    pytest.param(emails_utils.send_template_emails, {'template': 'emails/email_test.html'}, id='with template'),
    pytest.param(emails_utils.send_emails, {'subject': 'Test', 'content': 'Test'}, id='no template'),
])
def test_emails_with_attachments(settings, fct, kwargs):
    file_path = testapp.__path__[0] + '/templates/emails/email_error.html'
    recipients = [User(email='test@test.com')]
    success, sent = fct(recipients=recipients, attachments=[file_path], **kwargs)
    with open(file_path, 'r') as fo:
        expected = fo.read()
    assert success is True
    assert sent == ['test@test.com']
    assert [m.to[0] for m in dj_mail.outbox] == ['test@test.com']
    assert dj_mail.outbox[0].attachments == [('email_error.html', expected, 'text/html')]


@pytest.mark.parametrize('with_template', [
    pytest.param(True, id='with template'),
    pytest.param(False, id='no template'),
])
def test_send_error_report_emails(settings, with_template):
    if with_template:
        settings.EMAIL_ERROR_TEMPLATE = 'emails/email_error.html'

    success, sent = emails_utils.send_error_report_emails(
        title='The title', error='The error', recipients='test@test.com'
    )
    assert success is True
    assert sent == ['test@test.com']
    assert [m.to[0] for m in dj_mail.outbox] == ['test@test.com']
    assert dj_mail.outbox[0].subject == 'Error report - The title'
    body = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '-date-', dj_mail.outbox[0].body)
    body = re.sub(r'Unix user: .*<br/>', 'Unix user: -user-<br/>', body)
    body = re.sub(r'System hostname: .*</div>', 'System hostname: -host-</div>', body)
    expected = '''
<div style="margin-bottom: 8px;">Message sent at: -date-<br/>
Unix user: -user-<br/>
System hostname: -host-</div>
<fieldset style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;">
<legend><b> Error </b></legend>
<div>The error</div>
</fieldset>
<fieldset style="margin-bottom: 8px; border: 1px solid #888; border-radius: 4px;">
<legend><b> Traceback </b></legend>
<div>NoneType: None
<br/></div>
</fieldset>
'''.lstrip()
    if with_template:
        expected = f'\n<h2>With template!</h2>\n{expected}'
    assert body == expected
