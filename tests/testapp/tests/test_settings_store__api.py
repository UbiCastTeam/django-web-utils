import datetime

import pytest

from django_web_utils.settings_store.models import AbstractSettingsModel
from django_web_utils.settings_store.store import SettingsStoreBase, InvalidSetting
from testapp.models import SettingsStore, SettingsModel

pytestmark = pytest.mark.django_db


def get_new_setting_store(*args, **kwargs):
    settings_store = SettingsStore(*args, **kwargs)
    settings_store.cleanup_settings()
    return settings_store


def test_settings_store__subclassing__bad(django_assert_num_queries):
    with django_assert_num_queries(0):
        def subclass():
            class __BadSettingsStore(SettingsStoreBase):
                pass
        with pytest.raises(TypeError):
            subclass()

        def subclass():
            class __BadSettingsStore(SettingsStoreBase, model=AbstractSettingsModel):
                pass
        with pytest.raises(TypeError):
            subclass()

        class _BadSettingsStore(
            SettingsStoreBase,
            model='django_web_utils.settings_store.models.AbstractSettingsModel'
        ):
            pass
        with pytest.raises(TypeError):
            _BadSettingsStore().model


def test_settings_store__subclassing__good(django_assert_num_queries):
    with django_assert_num_queries(0):
        class GoodSettingsStore(
            SettingsStoreBase,
            model='testapp.models.SettingsModel'
        ):
            pass
        assert GoodSettingsStore().model == SettingsModel

        class GoodSettingsStore(SettingsStoreBase, model=SettingsModel):
            pass
        assert GoodSettingsStore().model == SettingsModel


def test_settings_store__frozen(django_assert_num_queries):
    with django_assert_num_queries(0):
        settings_store = SettingsStore()

        with pytest.raises(TypeError):
            settings_store.STR_VAL = 5

        with pytest.raises(TypeError):
            settings_store['STR_VAL'] = 5

        settings_store.not_a_setting = 5
        assert settings_store.not_a_setting == 5


def test_settings_store__get_defaults(django_assert_num_queries):
    with django_assert_num_queries(0):
        settings_store = SettingsStore()
        assert settings_store.get_default('STR_VAL') == 'foo'
        assert settings_store.get_default('FLOAT_VAL') == 5.5
        assert settings_store.get_default('DICT_VAL') == {'key': 'value'}
        assert settings_store.get_default('LIST_VAL') == [1, 2, 3, 4, 5]

    with django_assert_num_queries(1):
        assert settings_store.STR_VAL == 'foo'
    with django_assert_num_queries(0):
        assert settings_store.FLOAT_VAL == 5.5
        assert settings_store.DICT_VAL == {'key': 'value'}
        assert settings_store.LIST_VAL == [1, 2, 3, 4, 5]


def test_settings_store__refresh__simple(django_assert_num_queries):
    """
    Tests that refresh works as expected when a second "process" updates
    the settings.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(1):
        assert settings_store.STR_VAL == 'foo'  # query
        assert settings_store.get_default('STR_VAL') == 'foo'

    # Pretend another process updated the value in the database
    get_new_setting_store().update(STR_VAL='foo_2')
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo'
        assert settings_store.get_default('STR_VAL') == 'foo'

    with django_assert_num_queries(1):
        settings_store.refresh()
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_2'
        assert settings_store.get_default('STR_VAL') == 'foo'


def test_settings_store__refresh__with_obsolete_data_in_db(django_assert_num_queries):
    """
    Tests that refresh works as expected when obsolete data are in the db.
    """
    settings_store = get_new_setting_store()
    settings_store.model.objects.create(key='OBS_VAL', value='obsolete', updated_at=datetime.datetime.now())
    with django_assert_num_queries(0):
        with pytest.raises(AttributeError):
            settings_store.OBS_VAL

    # Pretend another process updated a value in the database
    get_new_setting_store().update(STR_VAL='foo_2')
    with django_assert_num_queries(1):
        settings_store.refresh()
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_2'
        with pytest.raises(AttributeError):
            settings_store.OBS_VAL


def test_settings_store__refresh__cached(django_assert_num_queries):
    """
    Tests that refresh works as expected when a cache_ttl is provided.
    """
    settings_store = SettingsStore(cache_ttl=3600)
    with django_assert_num_queries(1):
        assert settings_store.STR_VAL == 'foo'
        assert settings_store.get_default('STR_VAL') == 'foo'

    # Pretend another process updated the value in the database
    get_new_setting_store().update(STR_VAL='foo_2')
    with django_assert_num_queries(0):
        settings_store.refresh()
        assert settings_store.STR_VAL == 'foo'
        assert settings_store.get_default('STR_VAL') == 'foo'

    with django_assert_num_queries(1):
        settings_store.refresh(force=True)
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_2'
        assert settings_store.get_default('STR_VAL') == 'foo'


def test_settings_store__refresh__full(django_assert_num_queries):
    """
    Tests that refresh works as expected when full=True is passed.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(STR_VAL='foo_1')
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_1'

    # Pretend a value was updated in the db without setting its updated_at
    settings_store.model.objects.filter(key='STR_VAL').update(value='foo_2')
    with django_assert_num_queries(1):
        settings_store.refresh()
        assert settings_store.STR_VAL == 'foo_1'

    with django_assert_num_queries(1):
        settings_store.refresh(full=True)
        assert settings_store.STR_VAL == 'foo_2'


def test_settings_store__update__first_update(django_assert_num_queries):
    """
    Tests that update works when no keys exist in the database.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
            DICT_VAL={'key_upd': 'value_upd'},
            LIST_VAL=list(range(6, 11)),
        )
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_upd'
        assert settings_store.get_default('STR_VAL') == 'foo'

        assert settings_store.FLOAT_VAL == 6.6
        assert settings_store.get_default('FLOAT_VAL') == 5.5

        assert settings_store.DICT_VAL == {'key_upd': 'value_upd'}
        assert settings_store.get_default('DICT_VAL') == {'key': 'value'}

        assert settings_store.LIST_VAL == [6, 7, 8, 9, 10]
        assert settings_store.get_default('LIST_VAL') == [1, 2, 3, 4, 5]


def test_settings_store__update__with_none(django_assert_num_queries):
    """
    Tests that update works when no keys exist in the database.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(STR_VAL=None)
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL is None
        assert settings_store.get_default('STR_VAL') == 'foo'


def test_settings_store__update__without_cleanup_settings_first(django_assert_num_queries):
    """
    Tests that update raises when some keys already exist in the database
    and others don't (`.cleanup_settings()` has not been called).
    """
    settings_store = SettingsStore()
    with pytest.raises(RuntimeError):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
        )

    settings_store.cleanup_settings()
    with django_assert_num_queries(7):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
        )
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_upd'
        assert settings_store.FLOAT_VAL == 6.6
        assert settings_store.DICT_VAL == {'key': 'value'}
        assert settings_store.LIST_VAL == [1, 2, 3, 4, 5]


def test_settings_store__update__using_django_combinable(django_assert_num_queries):
    """
    Tests that update works when some keys are given combinable values
    (django functions or django F objects).
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=lambda x: x + 1.1,
            LIST_VAL=lambda x: x + [6],
        )
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_upd'
        assert settings_store.FLOAT_VAL == 6.6
        assert settings_store.DICT_VAL == {'key': 'value'}
        assert settings_store.LIST_VAL == [1, 2, 3, 4, 5, 6]


def test_settings_store__update__with_caching(django_assert_num_queries):
    """
    Tests that update works when caching is enabled.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(STR_VAL='foo_1')
        assert settings_store.STR_VAL == 'foo_1'

    settings_store = get_new_setting_store(cache_ttl=3600)
    with django_assert_num_queries(1):
        assert settings_store.STR_VAL == 'foo_1'
    with django_assert_num_queries(7):
        settings_store.update(STR_VAL='foo_2')
    with django_assert_num_queries(0):
        assert settings_store.STR_VAL == 'foo_2'


def test_settings_store__update__wrong_names(django_assert_num_queries):
    """
    Tests that update raises if the wrong setting names are passed.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(0):
        with pytest.raises(InvalidSetting):
            settings_store.update(NO_EXIST='foo_1')


def test_settings_store__update__wrong_values(django_assert_num_queries):
    """
    Tests that update performs custom validation.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(5):
        with pytest.raises(ValueError):
            settings_store.update(FLOAT_VAL=100)


def test_settings_store__mapping_interface(django_assert_num_queries):
    """
    Tests that the settings store acts like an immutable mapping.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
        )
    with django_assert_num_queries(0):
        assert settings_store['STR_VAL'] == 'foo_upd'
        assert settings_store['FLOAT_VAL'] == 6.6
        assert settings_store['DICT_VAL'] == {'key': 'value'}
        assert settings_store['LIST_VAL'] == [1, 2, 3, 4, 5]
        assert len(settings_store) == 4
        assert [k for k in settings_store] == ['STR_VAL', 'FLOAT_VAL', 'DICT_VAL', 'LIST_VAL']
        assert list(settings_store.keys()) == ['STR_VAL', 'FLOAT_VAL', 'DICT_VAL', 'LIST_VAL']
        assert list(settings_store.values()) == ['foo_upd', 6.6, {'key': 'value'}, [1, 2, 3, 4, 5]]
        assert list(settings_store.items()) == [
            ('STR_VAL', 'foo_upd'),
            ('FLOAT_VAL', 6.6), ('DICT_VAL', {'key': 'value'}),
            ('LIST_VAL', [1, 2, 3, 4, 5])]
        assert 'STR_VAL' in settings_store
        assert 'FLOAT_VAL' in settings_store
        assert 'DICT_VAL' in settings_store
        assert 'LIST_VAL' in settings_store


def test_settings_store__override(django_assert_num_queries):
    """
    Tests the settings store's override method.
    """
    settings_store = get_new_setting_store()
    with django_assert_num_queries(7):
        settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
        )
    assert settings_store.STR_VAL == 'foo_upd'
    assert settings_store.FLOAT_VAL == 6.6

    @settings_store.override(LIST_VAL=[6, 7, 8])
    class Klass:
        @settings_store.override(STR_VAL='foo_over')
        def test_something(_):
            with settings_store.override(FLOAT_VAL=8.8):
                settings_store.refresh(full=True)  # no effects on overrides
                assert settings_store['STR_VAL'] == 'foo_over'
                assert settings_store['FLOAT_VAL'] == 8.8
                assert settings_store['LIST_VAL'] == [6, 7, 8]
            assert settings_store['STR_VAL'] == 'foo_over'
            assert settings_store['FLOAT_VAL'] == 6.6
            assert settings_store['LIST_VAL'] == [6, 7, 8]

    Klass().test_something()
    assert settings_store.STR_VAL == 'foo_upd'
    assert settings_store.FLOAT_VAL == 6.6
    assert settings_store.LIST_VAL == [1, 2, 3, 4, 5]


def test_settings_store__cleanup_settings(django_assert_num_queries):
    assert SettingsModel.objects.count() == 0
    SettingsModel.objects.create(key='STR_VAL', value='foo_upd')
    SettingsModel.objects.create(key='FLOAT_VAL', value=6.6)
    SettingsModel.objects.create(key='OBSOLETE', value='obsolete')
    assert SettingsModel.objects.count() == 3

    settings_store = SettingsStore()
    with django_assert_num_queries(5):
        settings_store.cleanup_settings()
    db_rows = SettingsModel.objects.all()
    assert len(db_rows) == 4
    db_rows = {db_row.key: db_row for db_row in db_rows}
    assert db_rows['STR_VAL'].value == 'foo_upd'
    assert db_rows['FLOAT_VAL'].value == 6.6
    assert db_rows['DICT_VAL'].value == {'key': 'value'}
    assert db_rows['LIST_VAL'].value == [1, 2, 3, 4, 5]
