from unittest import mock

import pytest
from django.utils.translation import gettext_lazy as _

from testapp.forms import SettingsStoreValForm, SettingsStoreValFileForm

from .test_settings_store__api import get_new_setting_store

pytestmark = pytest.mark.django_db


def test_settings_store_form():
    settings_store = get_new_setting_store()
    assert settings_store.STR_VAL == 'foo'
    assert settings_store.FLOAT_VAL == 5.5

    form = SettingsStoreValForm({'str_val': 'foo_upd', 'float_val': 6.6}, settings_store=settings_store)
    assert form.initial == {'str_val': 'foo', 'float_val': 5.5}
    assert form.Meta.default_values == {'str_val': 'foo', 'float_val': 5.5}
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active in a few seconds.')

    assert settings_store.STR_VAL == 'foo_upd'
    assert settings_store.FLOAT_VAL == 6.6


def test_settings_store_form__initial():
    settings_store = get_new_setting_store()
    settings_store.update(STR_VAL='foo_upd', FLOAT_VAL=6.6)
    assert settings_store.STR_VAL == 'foo_upd'
    assert settings_store.FLOAT_VAL == 6.6

    form = SettingsStoreValForm({'str_val': 'foo_upd_2', 'float_val': 7.7}, settings_store=settings_store)
    assert form.initial == {'str_val': 'foo_upd', 'float_val': 6.6}
    assert form.Meta.default_values == {'str_val': 'foo', 'float_val': 5.5}
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active in a few seconds.')

    assert settings_store.STR_VAL == 'foo_upd_2'
    assert settings_store.FLOAT_VAL == 7.7


@mock.patch('django_web_utils.forms_utils.set_settings')
def test_settings_store_form__file_settings_form_compat(mock_set_settings):
    settings_store = get_new_setting_store()
    assert settings_store.STR_VAL == 'foo'
    assert settings_store.FLOAT_VAL == 5.5

    form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=settings_store)
    assert form.initial == {'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'}
    assert form.Meta.default_values == {'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'}
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active in a few seconds.')

    assert settings_store.STR_VAL == 'foo_upd'
    assert settings_store.FLOAT_VAL == 6.6
    mock_set_settings.assert_called_once_with([('FILE_VAL', 'foo_file_upd')])


@mock.patch('django_web_utils.forms_utils.set_settings')
def test_settings_store_form__file_settings_form_compat__success_message_from_file_settings_form(mock_set_settings):
    mock_set_settings.return_value = (True, _('Your changes will be active after the service restart.'))

    # No change in SettingsStore -> FileSettingsForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active after the service restart.')

    # Change in SettingsStore -> SettingsStoreForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active in a few seconds.')


@mock.patch('django_web_utils.forms_utils.set_settings')
def test_settings_store_form__file_settings_form_compat__no_change_from_file_settings_form(mock_set_settings):
    mock_set_settings.return_value = (True, _('No changes to save.'))

    # No change in SettingsStore -> SettingsStoreForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is True
    assert msg == _('No changes to save.')

    # Change in SettingsStore -> SettingsStoreForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is True
    assert msg == _('Your changes will be active in a few seconds.')


@mock.patch('django_web_utils.forms_utils.set_settings')
def test_settings_store_form__file_settings_form_compat__error_from_file_settings_form(mock_set_settings):
    mock_set_settings.return_value = (False, _('Unable to write configuration file'))

    # No change in SettingsStore -> FileSettingsForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is False
    assert msg == _('Unable to write configuration file')

    # Change in SettingsStore -> FileSettingsForm msg is returned
    form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
    success, msg = form.save()
    assert success is False
    assert msg == _('Unable to write configuration file')
