import argparse
from datetime import datetime
from io import StringIO
import json
import sys

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from django_web_utils.users_utils import UserManagement

pytestmark = pytest.mark.django_db


@pytest.fixture()
def users(password_generator):
    items = {
        'minimal': User(
            username='minimal',
        ),
        'partial': User(
            username='partial',
            email='partial@example.local',
        ),
        'complete': User(
            username='complete',
            first_name='Cømplète',
            last_name='Usér !',
            email='complete@example.local',
            password=password_generator('The pwd'),
        ),
    }
    items['complete'].last_connection = datetime.now()
    User.objects.bulk_create(items.values())
    return items


# --- Help ---

@pytest.mark.parametrize('args', [
    pytest.param(['-h'], id='global'),
    pytest.param(['list', '-h'], id='list'),
    pytest.param(['create', '-h'], id='create'),
    pytest.param(['update', '-h'], id='update'),
    pytest.param(['notify', '-h'], id='notify'),
    pytest.param(['delete', '-h'], id='delete'),
])
def test_help(capsys, args):
    with pytest.raises(SystemExit):
        call_command('user', *args, stdout=sys.stdout)
    captured = capsys.readouterr()
    assert captured.out.startswith('usage:')


# --- List ---

@pytest.mark.parametrize('header', [
    pytest.param(True, id='with header'),
    pytest.param(False, id='without header'),
])
def test_user_list(users, header):
    extra_args = [] if header else ['--no-header']
    out = StringIO()
    call_command('user', 'list', '-f', 'id,username,date_joined,last_login', *extra_args, stdout=out)
    output = out.getvalue()
    expected = '\t'.join(['id', 'username', 'date_joined', 'last_login']) + '\n' if header else ''
    expected += '\n'.join([
        f'{user.id}\t{user.username}\t{user.date_joined}\t{user.last_login}'
        for user in users.values()
    ]) + '\n'
    assert output == expected


@pytest.mark.parametrize('header', [
    pytest.param(True, id='with header'),
    pytest.param(False, id='without header'),
])
def test_user_list__csv(users, header):
    extra_args = [] if header else ['--no-header']
    out = StringIO()
    call_command('user', 'list', '-f', 'username,email', '-o', 'csv', *extra_args, stdout=out)
    output = out.getvalue().strip()
    expected = '"username","email"\n' if header else ''
    expected += '\n'.join([f'"{user.username}","{user.email}"' for user in users.values()])
    assert output == expected


def test_user_list__json(users):
    out = StringIO()
    call_command('user', 'list', '-f', 'username,first_name,password', '-o', 'json', stdout=out)
    output = out.getvalue()
    assert output.startswith('[\n  {\n    "username": "')
    data = json.loads(output)
    expected = [
        {
            'username': user.username,
            'first_name': user.first_name,
            'password': '***' if user.username == 'complete' else ''
        }
        for user in users.values()
    ]
    assert data == expected



def test_user_list__with_debug(users):
    out = StringIO()
    call_command('user', '-v', '3', 'list', '-f', 'username,email', '-o', 'csv', stdout=out)
    output = out.getvalue().strip()
    assert output.startswith('Ruuning cleaning for action "list" with options: {')
    assert 'Ruuning action "list" with options: {' in output
    assert output.endswith(
        '"username","email"\n'
        + '\n'.join([f'"{user.username}","{user.email}"' for user in users.values()])
    )


def test_user_list__filter(users):
    out = StringIO()
    call_command('user', 'list', '--username', 'complete', '-o', 'json', stdout=out)
    data = json.loads(out.getvalue())
    assert len(data) == 1
    assert data[0]['username'] == 'complete'


def test_user_list__filter_no_match(users):
    out = StringIO()
    call_command('user', 'list', '--username', 'does_not_exist', '-o', 'json', stdout=out)
    data = json.loads(out.getvalue())
    assert data == []


def test_user_list__all_fields(users):
    out = StringIO()
    call_command('user', 'list', '-o', 'json', stdout=out)
    data = json.loads(out.getvalue())
    assert len(data) == len(users)
    for row in data:
        for field in ('id', 'username', 'first_name', 'last_name', 'email', 'is_active'):
            assert field in row


def test_user_list__invalid_field():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'list', '-f', 'unknown_field', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == 'Error: argument -f/--fields: The field "unknown_field" is unknown.'


@pytest.mark.parametrize('limit', [
    pytest.param(True, id='with limit'),
    pytest.param(False, id='without limit'),
])
def test_user_list__too_many(limit):
    users = [
        User(username=f'user-{i}')
        for i in range(101)
    ]
    User.objects.bulk_create(users)

    out = StringIO()
    if limit:
        with pytest.raises(CommandError) as err:
            call_command('user', 'list', stdout=out)
        assert out.getvalue().strip() == ''
        assert str(err.value) == 'Too many users (> 100). Add --unlimited to see all users.'
    else:
        call_command('user', 'list', '--no-header', '--unlimited', stdout=out)
        output = out.getvalue().strip()
        assert len(output.split('\n')) == 101


# --- Create ---

def test_user_create__minimal():
    out = StringIO()
    call_command('user', 'create', '--username', 'new_user', stdout=out)
    user_id = out.getvalue().strip()
    assert user_id.isdigit()
    user = User.objects.get(pk=int(user_id))
    assert user.username == 'new_user'
    assert not user.has_usable_password()


def test_user_create__with_all_fields():
    out = StringIO()
    call_command(
        'user', 'create',
        '--username', 'full_user',
        '--first_name', 'John',
        '--last_name', 'Doe',
        '--email', 'john@example.local',
        '--password', 'S3cur3Pwd!',
        '--is_staff', 'True',
        stdout=out,
    )
    user_id = out.getvalue().strip()
    assert user_id.isdigit()
    user = User.objects.get(pk=int(user_id))
    assert user.username == 'full_user'
    assert user.first_name == 'John'
    assert user.last_name == 'Doe'
    assert user.email == 'john@example.local'
    assert user.check_password('S3cur3Pwd!')
    assert user.is_staff is True


def test_user_create__duplicate_username(users):
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '--username', 'minimal', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == "{'username': ['A user with that username already exists.']}"


def test_user_create__invalid_email():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '--username', 'bad_email', '--email', 'not-an-email', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == "{'email': ['Enter a valid email address.']}"


def test_user_create__json():
    out = StringIO()
    call_command('user', 'create', '-j', '{"username": "json_user"}', stdout=out)
    user_id = out.getvalue().strip()
    assert user_id.isdigit()
    user = User.objects.get(pk=int(user_id))
    assert user.username == 'json_user'
    assert not user.has_usable_password()


def test_user_create__json_with_multiple_fields():
    payload = {
        'username': 'json_full',
        'first_name': 'Json',
        'last_name': 'User',
        'email': 'json@example.local',
        'password': 'S3cur3Pwd!',
    }
    out = StringIO()
    call_command('user', 'create', '-j', json.dumps(payload), stdout=out)
    user = User.objects.get(username='json_full')
    assert user.first_name == 'Json'
    assert user.last_name == 'User'
    assert user.email == 'json@example.local'
    assert user.check_password('S3cur3Pwd!')


def test_user_create__json_field_overridden_by_arg():
    payload = {'username': 'json_user', 'first_name': 'FromJson'}
    out = StringIO()
    call_command('user', 'create', '-j', json.dumps(payload), '--first_name', 'FromArg', stdout=out)
    user = User.objects.get(username='json_user')
    assert user.first_name == 'FromArg'


def test_user_create__json_and_args_merged():
    payload = {'first_name': 'Json', 'last_name': 'User'}
    out = StringIO()
    call_command('user', 'create', '-j', json.dumps(payload), '--username', 'merged_user', stdout=out)
    user = User.objects.get(username='merged_user')
    assert user.first_name == 'Json'
    assert user.last_name == 'User'


def test_user_create__json_auto_fix_type():
    out = StringIO()
    call_command('user', 'create', '-j', '{"username": true, "is_active": "0"}', stdout=out)
    user_id = out.getvalue().strip()
    assert user_id.isdigit()
    user = User.objects.get(pk=int(user_id))
    assert user.username == 'True'
    assert user.is_active is False


def test_user_create__json_missing_required_field():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', '{"first_name": "NoUsername"}', stdout=out)
    assert str(err.value) == 'Missing required field: username'
    assert out.getvalue().strip() == ''


def test_user_create__invalid_json():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', 'not valid json', '--username', 'x', stdout=out)
    assert 'Error: argument -j/--json: Invalid JSON:' in str(err.value)
    assert out.getvalue().strip() == ''


def test_user_create__json_not_a_dict():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', '["username", "test"]', '--username', 'x', stdout=out)
    assert str(err.value) == 'Error: argument -j/--json: JSON must be a dictionary.'
    assert out.getvalue().strip() == ''


def test_user_create__json_invalid_email():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', '{"username": "x", "email": "not-an-email"}', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == "{'email': ['Enter a valid email address.']}"


def test_user_create__json_invalid_type():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', '{"username": "test", "is_active": "not-a-boolean"}', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == "{'is_active': ['“not-a-boolean” value must be either True or False.']}"


def test_user_create__json_non_allowed_fields():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'create', '-j', '{"username": "test", "id": "24"}', stdout=out)
    assert out.getvalue().strip() == ''
    assert str(err.value) == 'The following fields are not allowed: id.'


# --- Update ---

def test_user_update__email(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '--target', f'username={user.username}',
        '--email', 'new@example.local',
        stdout=out,
    )
    user_id = out.getvalue().strip()
    assert user_id.isdigit()
    assert user_id == str(user.id)
    user.refresh_from_db()
    assert user.email == 'new@example.local'


def test_user_update__password(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '--password', 'NewPwd123!',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.check_password('NewPwd123!')


def test_user_update__set_unusable_password(users):
    user = users['complete']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '--password', '',
        stdout=out,
    )
    user.refresh_from_db()
    assert not user.has_usable_password()


def test_user_update__target_by_id(users):
    user = users['partial']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'id={user.id}',
        '--first_name', 'Updated',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.first_name == 'Updated'


def test_user_update__target_by_email(users):
    user = users['complete']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'email={user.email}',
        '--email', 'new@example.local',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.email == 'new@example.local'


@pytest.mark.parametrize('target', [
    pytest.param('username=does_not_exist', id='username'),
    pytest.param('email=does_not_exist@example.local', id='email'),
])
def test_user_update__nonexistent_user(target):
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command(
            'user', 'update',
            '-t', target,
            '--email', 'x@x.local',
            stdout=out,
        )
    assert str(err.value) == 'The requested user account does not exist.'
    assert out.getvalue().strip() == ''


@pytest.mark.parametrize('target, message', [
    pytest.param(
        'bad_format', 'Invalid format for "bad_format".',
        id='bad_format'
    ),
    pytest.param(
        '=test', 'No field specified in target.',
        id='no_field'
    ),
    pytest.param(
        'first_name=test', 'The target field is invalid. Allowed fields are: id, username, email.',
        id='invalid_field'
    ),
    pytest.param(
        'username=', 'No value specified in target.',
        id='no_value'
    ),
])
def test_user_update__invalid_target_format(target, message):
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'update', '-t', target, '--email', 'x@x.local', stdout=out)
    assert str(err.value) == f'Error: argument -t/--target: {message}'
    assert out.getvalue().strip() == ''


def test_user_update__via_json(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '-j', '{"email": "json@example.local"}',
        stdout=out,
    )
    user_id = out.getvalue().strip()
    assert user_id == str(user.id)
    user.refresh_from_db()
    assert user.email == 'json@example.local'


def test_user_update__json_with_multiple_fields(users):
    user = users['minimal']
    payload = {'first_name': 'Json', 'last_name': 'Updated', 'email': 'json@example.local'}
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '-j', json.dumps(payload),
        stdout=out,
    )
    user.refresh_from_db()
    assert user.first_name == 'Json'
    assert user.last_name == 'Updated'
    assert user.email == 'json@example.local'


def test_user_update__json_field_overridden_by_arg(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '-j', '{"first_name": "FromJson"}',
        '--first_name', 'FromArg',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.first_name == 'FromArg'


def test_user_update__json_and_args_merged(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '-j', '{"first_name": "Json"}',
        '--last_name', 'FromArg',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.first_name == 'Json'
    assert user.last_name == 'FromArg'


def test_user_update__json_password(users):
    user = users['minimal']
    out = StringIO()
    call_command(
        'user', 'update',
        '-t', f'username={user.username}',
        '-j', '{"password": "NewPwd123!"}',
        stdout=out,
    )
    user.refresh_from_db()
    assert user.check_password('NewPwd123!')


def test_user_update__invalid_json(users):
    user = users['minimal']
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command(
            'user', 'update',
            '-t', f'username={user.username}',
            '-j', 'not valid json',
            stdout=out,
        )
    assert 'Error: argument -j/--json: Invalid JSON:' in str(err.value)
    assert out.getvalue().strip() == ''


def test_user_update__json_not_a_dict(users):
    user = users['minimal']
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command(
            'user', 'update',
            '-t', f'username={user.username}',
            '-j', '["email", "x@x.local"]',
            stdout=out,
        )
    assert str(err.value) == 'Error: argument -j/--json: JSON must be a dictionary.'
    assert out.getvalue().strip() == ''


# --- Notify ---

def test_user_notify__not_implemented(users):
    user = users['minimal']
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command(
            'user', 'notify',
            '-t', f'username={user.username}',
            stdout=out,
        )
    assert str(err.value) == 'This action is not implemented in this application.'
    assert out.getvalue().strip() == ''


# --- Delete ---

def test_user_delete(users):
    user = users['minimal']
    out = StringIO()
    call_command('user', 'delete', '-t', f'username={user.username}', stdout=out)
    assert not User.objects.filter(username=user.username).exists()
    assert out.getvalue().strip() == ''


def test_user_delete__by_email(users):
    user = users['complete']
    out = StringIO()
    call_command('user', 'delete', '-t', f'email={user.email}', stdout=out)
    assert not User.objects.filter(username=user.username).exists()
    assert out.getvalue().strip() == ''


def test_user_delete__nonexistent_user():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'delete', '-t', 'username=does_not_exist', stdout=out)
    assert str(err.value) == 'The requested user account does not exist.'
    assert out.getvalue().strip() == ''


def test_user_delete__invalid_target():
    out = StringIO()
    with pytest.raises(CommandError) as err:
        call_command('user', 'delete', '-t', 'bad_format', stdout=out)
    assert str(err.value) == 'Error: argument -t/--target: Invalid format for "bad_format".'
    assert out.getvalue().strip() == ''


# --- format_values ---

def test_format_values__password_set():
    obj = {'password': 'pbkdf2_sha256$...'}
    UserManagement.format_values(obj)
    assert obj['password'] == '***'


def test_format_values__password_unusable():
    obj = {'password': '!invalidhash'}
    UserManagement.format_values(obj)
    assert obj['password'] == ''


def test_format_values__password_empty():
    obj = {'password': ''}
    UserManagement.format_values(obj)
    assert obj['password'] == ''


def test_format_values__none_value():
    obj = {'email': None}
    UserManagement.format_values(obj)
    assert obj['email'] is None


def test_format_values__datetime_converted_to_str():
    dt = datetime(2024, 1, 15, 10, 30)
    obj = {'date_joined': dt}
    UserManagement.format_values(obj)
    assert obj['date_joined'] == '2024-01-15 10:30:00'


# --- validate_json ---

def test_validate_json__valid_dict():
    result = UserManagement.validate_json('{"key": "value", "count": "3"}')
    assert result == {'key': 'value', 'count': '3'}


def test_validate_json__empty_string():
    result = UserManagement.validate_json('')
    assert result is None


def test_validate_json__none_value():
    result = UserManagement.validate_json(None)
    assert result is None


@pytest.mark.parametrize('value, message', [
    pytest.param(
        'not json', 'Invalid JSON: Expecting value: line 1 column 1 (char 0)',
        id='wrong'
    ),
    pytest.param(
        '[1, 2, 3]', 'JSON must be a dictionary.',
        id='list'
    ),
    pytest.param(
        '"just a string"', 'JSON must be a dictionary.',
        id='string'
    ),
])
def test_validate_json__invalid(value, message):
    with pytest.raises(argparse.ArgumentTypeError) as err:
        UserManagement.validate_json(value)
    assert str(err.value) == message
