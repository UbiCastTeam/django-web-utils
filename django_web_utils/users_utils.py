"""
Script to manage the application user accounts.
"""
import argparse
import csv
import json
from typing import Any, TextIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Model, QuerySet


class UserManagement:
    """
    Class to manage the application user accounts.
    """
    # List of supported actions.
    ACTIONS = ['list', 'create', 'update', 'notify', 'delete']
    # List of all available fields.
    FIELDS = [
        'id', 'username', 'first_name', 'last_name', 'email', 'password',
        'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login'
    ]
    # List of required fields to create a user.
    REQUIRED_FIELDS = ['username']
    # List of unique fields that can be used to target a user.
    UNIQUE_FIELDS = ['id', 'username', 'email']
    # List of read-only fields.
    READ_ONLY_FIELDS = ['id', 'date_joined', 'last_login']
    # List of sensitive fields that should not be displayed.
    SENSITIVE_FIELDS = ['password']
    # The application's user model.
    MODEL = get_user_model()

    @classmethod
    def get_user_fields_repr(cls, only_unique: bool = False) -> str:
        fields_str = []
        for name in (cls.UNIQUE_FIELDS if only_unique else cls.FIELDS):
            field = cls.MODEL._meta.get_field(name)
            description = (
                str(field.verbose_name or name).capitalize()
                + str(field.help_text).strip('. \n').replace('\n', '\n  ')
            ).strip('. \n')
            fields_str.append(f'- "{name}": {description}.')
        return '\n'.join(fields_str)

    @classmethod
    def validate_json(cls, json_str: str | None) -> dict[str, str] | None:
        if not json_str:
            return None
        try:
            content = json.loads(json_str)
        except json.JSONDecodeError as err:
            raise argparse.ArgumentTypeError(f'Invalid JSON: {str(err)}') from err
        if not isinstance(content, dict):
            raise argparse.ArgumentTypeError('JSON must be a dictionary.')
        return content

    @classmethod
    def validate_field_names(cls, names: str) -> list[str]:
        names_lst = [clean_name for name in names.split(',') if (clean_name := name.strip())]
        for name in names_lst:
            cls.validate_field_name(name)
        return names_lst

    @classmethod
    def validate_field_name(cls, name: str) -> str:
        if name not in cls.FIELDS:
            raise argparse.ArgumentTypeError(f'The field "{name}" is unknown.')
        return name

    @classmethod
    def validate_target(cls, item: str) -> dict[str, str]:
        if '=' not in item:
            raise argparse.ArgumentTypeError(f'Invalid format for "{item}".')
        field, value = item.split('=', 1)
        if not field:
            raise argparse.ArgumentTypeError('No field specified in target.')
        if field not in cls.UNIQUE_FIELDS:
            raise argparse.ArgumentTypeError(
                f'The target field is invalid. Allowed fields are: {", ".join(cls.UNIQUE_FIELDS)}.'
            )
        if not value:
            raise argparse.ArgumentTypeError('No value specified in target.')
        cls.validate_field_name(field)
        return cls.validate_user_data({field: value})

    @classmethod
    def validate_user_data(cls, data: dict[str, str], allowed_fields: set[str] | None = None) -> dict[str, str]:
        if allowed_fields and (forbidden_fields := set(data.keys()) - allowed_fields):
            raise argparse.ArgumentTypeError(f'The following fields are not allowed: {", ".join(forbidden_fields)}.')

        dummy_user = cls.MODEL(**data)
        if 'password' in data:
            if data['password']:
                dummy_user.set_password(data['password'])
            else:
                dummy_user.set_unusable_password()
        try:
            dummy_user.clean_fields(exclude=[
                field.name
                for field in cls.MODEL._meta.get_fields()
                if field.name not in data
            ])
        except ValidationError as err:
            raise argparse.ArgumentTypeError(str(err)) from err

        # The "clean_fields" method will fix the type of values if incorrect, so return the fixed values
        cleaned_data = {field: getattr(dummy_user, field) for field in data}
        if 'password' in data:
            cleaned_data['password'] = data['password']
        return cleaned_data

    @classmethod
    def format_values(cls, object_dict: dict[str, Any]) -> None:
        for field, value in object_dict.items():
            if value is None:
                continue

            if field == 'password':  # Special case, handle unusable password
                value = bool(value and not value.startswith('!'))

            if field in cls.SENSITIVE_FIELDS:
                object_dict[field] = '' if not value else '***'
            elif not isinstance(value, (str, bool, int, float)):
                object_dict[field] = str(value)

    @classmethod
    def get_user_account(cls, filters: dict[str, Any]) -> Model:
        try:
            user = cls.MODEL.objects.get(**filters)
        except cls.MODEL.DoesNotExist as err:
            raise argparse.ArgumentTypeError('The requested user account does not exist.') from err
        return user

    @classmethod
    def get_user_accounts(cls, filters: dict[str, Any], fields: list[str]) -> QuerySet:
        queryset = cls.MODEL.objects.all().values(*fields)
        if filters:
            queryset = queryset.filter(**filters)
        return queryset

    @classmethod
    def add_parser__list(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            'list',
            help='List application user accounts.',
            formatter_class=argparse.RawTextHelpFormatter
        )
        for name in cls.FIELDS:
            field = cls.MODEL._meta.get_field(name)
            help_text = str(field.help_text).removeprefix('Required. ').replace('\n', '\n  ')
            subparser.add_argument(
                f'--{name}', dest=name, metavar=name.upper(), default=None,
                help=f'Filter results by {field.verbose_name or name} (exact value). \n{help_text}'.strip('. \n') + '.'
            )
        subparser.add_argument(
            '-f', '--fields', dest='fields', type=cls.validate_field_names,
            help='Fields to include in the output. \n'
                 'Separate multiple values with commas. \n'
                 'By default, all fields are present in the output. \n'
                 f'Available fields: {", ".join(cls.FIELDS)}. \n'
                 'Example: "-f \'username,first_name\'".',
        )
        subparser.add_argument(
            '-o', '--output', metavar='FORMAT', default='raw', choices=['raw', 'csv', 'json'],
            help='Output format to use. Allowed values: "raw" (default), "csv" or "json".'
        )
        subparser.add_argument(
            '-t', '--no-header', action='store_true',
            help='Do not display the header row in the output. \nNot applicable to JSON output.'
        )
        subparser.add_argument(
            '-n', '--unlimited', action='store_true',
            help='Do not limit the number of rows in the output. \nBy default, the output is limited to 100 rows.'
        )
        return subparser

    @classmethod
    def clean_options__list(cls, options: dict) -> None:
        options['fields'] = options.pop('fields', None) or cls.FIELDS

        options['filters'] = {
            name: val
            for name in cls.FIELDS
            if (val := options.pop(name)) is not None
        }
        cls.validate_user_data(options['filters'])

        queryset = cls.get_user_accounts(options['filters'], options['fields'])
        if not options['unlimited'] and queryset.count() > 100:
            raise CommandError('Too many users (> 100). Add --unlimited to see all users.')
        options['users'] = list(queryset)

    @classmethod
    def run_action__list(cls, stdout: TextIO, options: dict) -> None:
        users = options['users']
        for user in users:
            cls.format_values(user)
        if options['output'] == 'json':
            stdout.write(json.dumps(users, indent=2, ensure_ascii=False))
        elif options['output'] == 'csv':
            writer = csv.DictWriter(stdout, fieldnames=options['fields'], dialect='unix')
            if not options['no_header']:
                writer.writeheader()
            for user in users:
                writer.writerow(user)
        else:
            if not options['no_header']:
                stdout.write('\t'.join(options['fields']))
            for user in users:
                stdout.write('\t'.join(str(value) for value in user.values()))

    @classmethod
    def add_parser__create(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            'create',
            help='Create an application user account and return its identifier.',
            formatter_class=argparse.RawTextHelpFormatter
        )
        for name in cls.FIELDS:
            if name in cls.READ_ONLY_FIELDS:
                continue
            field = cls.MODEL._meta.get_field(name)
            help_text = str(field.help_text).replace('\n', '\n  ')
            subparser.add_argument(
                f'--{name}', dest=name, metavar=name.upper(), default=None,
                help=(str(field.verbose_name or name).capitalize() + '. \n' + help_text).strip('. \n') + '.'
            )
        subparser.add_argument(
            '-j', '--json', dest='json', default=None, type=cls.validate_json,
            help='The account field values as JSON content. \n'
                 'All fields described above can be used. \n'
                 'Example: "-j \'{"first_name": "test"}\'".',
        )
        return subparser

    @classmethod
    def clean_options__create(cls, options: dict) -> None:
        writable_fields = set(cls.FIELDS) - set(cls.READ_ONLY_FIELDS)
        data = options.pop('json') or {}
        data.update({
            name: val
            for name in writable_fields
            if (val := options.pop(name)) is not None
        })
        for field in cls.REQUIRED_FIELDS:
            if not data.get(field):
                raise argparse.ArgumentTypeError(f'Missing required field: {field}')
        options['data'] = cls.validate_user_data(data, allowed_fields=writable_fields)

    @classmethod
    def run_action__create(cls, stdout: TextIO, options: dict) -> Model:
        user = cls.MODEL(**options['data'])
        if cls.MODEL._meta.get_field('password'):
            if options['data'].get('password'):
                user.set_password(options['data']['password'])
            else:
                user.set_unusable_password()
        user.full_clean()
        user.save()
        stdout.write(str(user.id))
        return user

    @classmethod
    def add_parser__update(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            'update',
            help='Update an application user account and return its identifier.',
            formatter_class=argparse.RawTextHelpFormatter
        )
        subparser.add_argument(
            '-t', '--target', dest='target', metavar='FIELD=VALUE', type=cls.validate_target,
            help='The targeted user account. \n'
                 f'Available fields: \n{cls.get_user_fields_repr(True)} \n'
                 'Example: "-t id=42".',
        )
        for name in cls.FIELDS:
            if name in cls.READ_ONLY_FIELDS:
                continue
            field = cls.MODEL._meta.get_field(name)
            help_text = str(field.help_text).replace('\n', '\n  ')
            subparser.add_argument(
                f'--{name}', dest=name, metavar=name.upper(), default=None,
                help=(str(field.verbose_name or name).capitalize() + '. \n' + help_text).strip('. \n') + '.'
            )
        subparser.add_argument(
            '-j', '--json', dest='json', default=None, type=cls.validate_json,
            help='The account field values as JSON content. \n'
                 'All fields described above can be used. \n'
                 'Example: "-j \'{"first_name": "test"}\'".',
        )
        return subparser

    @classmethod
    def clean_options__update(cls, options: dict) -> None:
        options['user'] = cls.get_user_account(options['target'])

        writable_fields = set(cls.FIELDS) - set(cls.READ_ONLY_FIELDS)
        data = options.pop('json') or {}
        data.update({
            name: val
            for name in writable_fields
            if (val := options.pop(name)) is not None
        })
        options['data'] = cls.validate_user_data(data, allowed_fields=writable_fields)

    @classmethod
    def run_action__update(cls, stdout: TextIO, options: dict) -> Model:
        user = options['user']

        changed = []
        for name, value in options['data'].items():
            if name == 'password':
                if value:
                    user.set_password(value)
                else:
                    user.set_unusable_password()
            else:
                setattr(user, name, value)
            changed.append(name)

        user.full_clean(exclude=[
            field.name
            for field in cls.MODEL._meta.get_fields()
            if field.name not in changed
        ])
        user.save(update_fields=changed)
        stdout.write(str(user.id))
        return user

    @classmethod
    def add_parser__notify(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            'notify',
            help='Send an email to the user account, if he has an email address, \n'
                 'to inform him that he has an account.',
            formatter_class=argparse.RawTextHelpFormatter
        )
        subparser.add_argument(
            '-t', '--target', dest='target', metavar='FIELD=VALUE', type=cls.validate_target,
            help='The targeted user account. \n'
                 f'Available fields: \n{cls.get_user_fields_repr(True)} \n'
                 'Example: "-t id=42".',
        )
        return subparser

    @classmethod
    def clean_options__notify(cls, options: dict) -> None:
        options['user'] = cls.get_user_account(options['target'])

    @classmethod
    def run_action__notify(cls, stdout: TextIO, options: dict) -> Model:
        raise CommandError('This action is not implemented in this application.')

    @classmethod
    def add_parser__delete(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(
            'delete',
            help='Delete an application user account.',
            formatter_class=argparse.RawTextHelpFormatter,
        )
        subparser.add_argument(
            '-t', '--target', dest='target', metavar='FIELD=VALUE', type=cls.validate_target,
            help='The targeted user account. \n'
                 f'Available fields: \n{cls.get_user_fields_repr(True)} \n'
                 'Example: "-t id=42".',
        )
        return subparser

    @classmethod
    def clean_options__delete(cls, options: dict) -> None:
        options['user'] = cls.get_user_account(options['target'])

    @classmethod
    def run_action__delete(cls, stdout: TextIO, options: dict) -> Model:
        user = options['user']
        user.delete()
        return user


class UserCommand(BaseCommand):
    help = __doc__.strip()

    management_class: type[UserManagement] = UserManagement

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        subparsers = parser.add_subparsers(
            title='action', dest='action', required=True,
            help='The action to run.'
        )
        for action in self.management_class.ACTIONS:
            getattr(self.management_class, f'add_parser__{action}')(subparsers)

    def handle(self, *args, **options) -> None:
        options['debug'] = options['verbosity'] > 1
        if options['debug']:
            self.stdout.write(f'Ruuning cleaning for action "{options["action"]}" with options: {options}')
        try:
            getattr(self.management_class, f'clean_options__{options["action"]}')(options)
        except argparse.ArgumentTypeError as err:
            raise CommandError(str(err)) from err
        if options['debug']:
            self.stdout.write(f'Ruuning action "{options["action"]}" with options: {options}')
        try:
            getattr(self.management_class, f'run_action__{options["action"]}')(self.stdout, options)
        except ValidationError as err:
            raise CommandError(str(err)) from err
