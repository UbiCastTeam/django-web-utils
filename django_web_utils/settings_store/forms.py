from typing import Type

# Django
from django import forms as dj_forms
from django.utils.translation import gettext_lazy as _

from django_web_utils.forms_utils import BaseFileSettingsForm
from .store import SettingsStoreBase


class BaseSettingsStoreForm:
    '''
    Form designed to change settings in database.
    Settings that can be altered must be defined in Meta.SETTINGS_STORE_MAPPING.
    '''
    def __init__(self, *args, settings_store=None, **kwargs):
        initial = kwargs.setdefault('initial', dict())
        if settings_store:
            self.settings_store = settings_store
        elif not getattr(self, 'settings_store', None):
            raise RuntimeError('No settings store instance is defined.')

        self.settings_store.refresh(force=True)

        for field, info in self.Meta.SETTINGS_STORE_MAPPING.items():
            if field not in initial:
                name = info['setting']
                val = self.settings_store.get(name, self.settings_store.get_default(name))

                if isinstance(val, str) and '\n' in val and '\r' not in val:
                    # browsers inject \r in multi lines texts so do it before to have a correct changed_data value
                    val = val.replace('\n', '\r\n')
                initial[field] = val
        super().__init__(*args, **kwargs)

    class Meta:
        SETTINGS_STORE_MAPPING = {
            # <field>: {'setting': <name>}
        }

        @classmethod
        def get_default_values(cls, settings_store_cls: Type[SettingsStoreBase], mapping):
            default_values = {}
            for field, info in mapping.items():
                name = info['setting']
                default = settings_store_cls.get_default(name)
                if default is True:
                    default_values[field] = _('Yes')
                elif default is False:
                    default_values[field] = _('No')
                elif default:
                    default_values[field] = default
            return default_values

    def save(self, commit=True):
        """
        Returns: success (boolean), changed (list of fields names).
        """
        success, msg = None, None
        if hasattr(super(), 'save'):
            result = super().save(commit)
            # Compat with django_web_utils.forms_utils.BaseFileSettingsForm
            if isinstance(self, BaseFileSettingsForm) and hasattr(result, '__len__') and len(result) == 2 and isinstance(result[0], bool):
                success, msg = result
                if success is False:
                    return success, msg

        # Settings fields
        changed = {}
        for field, info in self.Meta.SETTINGS_STORE_MAPPING.items():
            name = info['setting']
            default = self.settings_store.get_default(name)
            value = self.cleaned_data.get(field, default)
            current_value = self.settings_store.get(name, default)
            if value != current_value:
                changed[name] = value
        # Write changes to database
        if commit:
            if not changed:
                if success is None or not self.has_changed():
                    return True, _('No changes to save.')
                return success, msg
            self.settings_store.update(**changed)
            return True, _('Your changes will be active in a few seconds.')
        return True, list(changed.items()) + (msg if isinstance(msg, list) else ())


class SettingsStoreForm(BaseSettingsStoreForm, dj_forms.Form):
    def save(self, commit=True):
        if self.errors:
            raise ValueError(f'The form could not be saved: {self.errors}')
        return super().save(commit=commit)


class SettingsStoreModelForm(BaseSettingsStoreForm, dj_forms.ModelForm):
    pass
