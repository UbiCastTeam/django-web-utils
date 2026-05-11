from django_web_utils.settings_store.models import AbstractSettingsModel
from django_web_utils.settings_store.store import SettingsStoreBase


class SettingsModel(AbstractSettingsModel):
    pass


class SettingsStore(SettingsStoreBase, model=SettingsModel):
    STR_VAL: str = 'foo'
    FLOAT_VAL: float = 5.5
    DICT_VAL: dict = {'key': 'value'}
    LIST_VAL: list = [1, 2, 3, 4, 5]

    def _validate(self, **settings):
        if 'FLOAT_VAL' in settings and settings['FLOAT_VAL'] >= 100:
            raise ValueError('value must be < 100')
