"""
Settings utils tests.
"""
import datetime
from contextlib import contextmanager
from unittest import mock

from django.db import connections
from django.db.utils import load_backend, OperationalError
from django.test import TestCase, TransactionTestCase
from django.utils.translation import gettext_lazy as _

from django_web_utils.settings_store.models import AbstractSettingsModel
from django_web_utils.settings_store.store import SettingsStoreBase, InvalidSetting

from testapp.forms import SettingsStoreValForm, SettingsStoreValFileForm
from testapp.models import SettingsStore, SettingsModel


def get_new_setting_store(*args, **kwargs):
    settings_store = SettingsStore(*args, **kwargs)
    settings_store.cleanup_settings()
    return settings_store


class SettingsStoreTests(TestCase):
    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_settings_store__subclassing__bad(self):
        with self.assertNumQueries(0):
            def subclass():
                class __BadSettingsStore(SettingsStoreBase):
                    pass
            self.assertRaises(TypeError, subclass)

            def subclass():
                class __BadSettingsStore(SettingsStoreBase, model=AbstractSettingsModel):
                    pass
            self.assertRaises(TypeError, subclass)

            class _BadSettingsStore(
                SettingsStoreBase,
                model='django_web_utils.settings_store.models.AbstractSettingsModel'
            ):
                pass
            self.assertRaises(TypeError, lambda: _BadSettingsStore().model)

    def test_settings_store__subclassing__good(self):
        with self.assertNumQueries(0):
            class GoodSettingsStore(
                SettingsStoreBase,
                model='testapp.models.SettingsModel'
            ):
                pass
            self.assertEqual(GoodSettingsStore().model, SettingsModel)

            class GoodSettingsStore(SettingsStoreBase, model=SettingsModel):
                pass
            self.assertEqual(GoodSettingsStore().model, SettingsModel)

    def test_settings_store__frozen(self):
        with self.assertNumQueries(0):
            settings_store = SettingsStore()

            def assign():
                settings_store.STR_VAL = 5
            self.assertRaises(TypeError, assign)

            def assign():
                settings_store['STR_VAL'] = 5
            self.assertRaises(TypeError, assign)

            settings_store.not_a_setting = 5
            self.assertEqual(settings_store.not_a_setting, 5)

    def test_settings_store__get_defaults(self):
        with self.assertNumQueries(0):
            settings_store = SettingsStore()
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')
            self.assertEqual(settings_store.get_default('FLOAT_VAL'), 5.5)
            self.assertEqual(settings_store.get_default('DICT_VAL'), {'key': 'value'})
            self.assertEqual(settings_store.get_default('LIST_VAL'), [1, 2, 3, 4, 5])

        with self.assertNumQueries(1):
            self.assertEqual(settings_store.STR_VAL, 'foo')
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.FLOAT_VAL, 5.5)
            self.assertEqual(settings_store.DICT_VAL, {'key': 'value'})
            self.assertEqual(settings_store.LIST_VAL, [1, 2, 3, 4, 5])

    def test_settings_store__refresh__simple(self):
        """
        Tests that refresh works as expected when a second "process" updates
        the settings.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(1):
            self.assertEqual(settings_store.STR_VAL, 'foo')  # query
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

        # Pretend another process updated the value in the database
        get_new_setting_store().update(STR_VAL='foo_2')
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

        with self.assertNumQueries(1):
            settings_store.refresh()
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_2')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

    def test_settings_store__refresh__with_obsolete_data_in_db(self):
        """
        Tests that refresh works as expected when obsolete data are in the db.
        """
        settings_store = get_new_setting_store()
        settings_store.model.objects.create(key='OBS_VAL', value='obsolete', updated_at=datetime.datetime.now())
        with self.assertNumQueries(0):
            self.assertRaises(AttributeError, lambda: settings_store.OBS_VAL)

        # Pretend another process updated a value in the database
        get_new_setting_store().update(STR_VAL='foo_2')
        with self.assertNumQueries(1):
            settings_store.refresh()
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_2')
            self.assertRaises(AttributeError, lambda: settings_store.OBS_VAL)

    def test_settings_store__refresh__cached(self):
        """
        Tests that refresh works as expected when a cache_ttl is provided.
        """
        settings_store = SettingsStore(cache_ttl=3600)
        with self.assertNumQueries(1):
            self.assertEqual(settings_store.STR_VAL, 'foo')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

        # Pretend another process updated the value in the database
        get_new_setting_store().update(STR_VAL='foo_2')
        with self.assertNumQueries(0):
            settings_store.refresh()
            self.assertEqual(settings_store.STR_VAL, 'foo')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

        with self.assertNumQueries(1):
            settings_store.refresh(force=True)
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_2')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

    def test_settings_store__refresh__full(self):
        """
        Tests that refresh works as expected when full=True is passed.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(STR_VAL='foo_1')
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_1')

        # Pretend a value was updated in the db without setting its updated_at
        settings_store.model.objects.filter(key='STR_VAL').update(value='foo_2')
        with self.assertNumQueries(1):
            settings_store.refresh()
            self.assertEqual(settings_store.STR_VAL, 'foo_1')

        with self.assertNumQueries(1):
            settings_store.refresh(full=True)
            self.assertEqual(settings_store.STR_VAL, 'foo_2')

    def test_settings_store__update__first_update(self):
        """
        Tests that update works when no keys exist in the database.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(
                STR_VAL='foo_upd',
                FLOAT_VAL=6.6,
                DICT_VAL={'key_upd': 'value_upd'},
                LIST_VAL=list(range(6, 11)),
            )
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_upd')
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

            self.assertEqual(settings_store.FLOAT_VAL, 6.6)
            self.assertEqual(settings_store.get_default('FLOAT_VAL'), 5.5)

            self.assertEqual(settings_store.DICT_VAL, {'key_upd': 'value_upd'})
            self.assertEqual(settings_store.get_default('DICT_VAL'), {'key': 'value'})

            self.assertEqual(settings_store.LIST_VAL, [6, 7, 8, 9, 10])
            self.assertEqual(settings_store.get_default('LIST_VAL'), [1, 2, 3, 4, 5])

    def test_settings_store__update__with_none(self):
        """
        Tests that update works when no keys exist in the database.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(STR_VAL=None)
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, None)
            self.assertEqual(settings_store.get_default('STR_VAL'), 'foo')

    def test_settings_store__update__without_cleanup_settings_first(self):
        """
        Tests that update raises when some keys already exist in the database
        and others don't (`.cleanup_settings()` has not been called).
        """
        settings_store = SettingsStore()
        self.assertRaises(RuntimeError, lambda: settings_store.update(
            STR_VAL='foo_upd',
            FLOAT_VAL=6.6,
        ))

        settings_store.cleanup_settings()
        with self.assertNumQueries(7):
            settings_store.update(
                STR_VAL='foo_upd',
                FLOAT_VAL=6.6,
            )
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_upd')
            self.assertEqual(settings_store.FLOAT_VAL, 6.6)
            self.assertEqual(settings_store.DICT_VAL, {'key': 'value'})
            self.assertEqual(settings_store.LIST_VAL, [1, 2, 3, 4, 5])

    def test_settings_store__update__using_django_combinable(self):
        """
        Tests that update works when some keys are given combinable values
        (django functions or django F objects).
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(
                STR_VAL='foo_upd',
                FLOAT_VAL=lambda x: x + 1.1,
                LIST_VAL=lambda x: x + [6],
            )
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_upd')
            self.assertEqual(settings_store.FLOAT_VAL, 6.6)
            self.assertEqual(settings_store.DICT_VAL, {'key': 'value'})
            self.assertEqual(settings_store.LIST_VAL, [1, 2, 3, 4, 5, 6])

    def test_settings_store__update__with_caching(self):
        """
        Tests that update works when caching is enabled.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(STR_VAL='foo_1')
            self.assertEqual(settings_store.STR_VAL, 'foo_1')

        settings_store = get_new_setting_store(cache_ttl=3600)
        with self.assertNumQueries(1):
            self.assertEqual(settings_store.STR_VAL, 'foo_1')
        with self.assertNumQueries(7):
            settings_store.update(STR_VAL='foo_2')
        with self.assertNumQueries(0):
            self.assertEqual(settings_store.STR_VAL, 'foo_2')

    def test_settings_store__update__wrong_names(self):
        """
        Tests that update raises if the wrong setting names are passed.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(0):
            self.assertRaises(InvalidSetting, lambda: settings_store.update(NO_EXIST='foo_1'))

    def test_settings_store__update__wrong_values(self):
        """
        Tests that update performs custom validation.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(5):
            self.assertRaises(ValueError, lambda: settings_store.update(FLOAT_VAL=100))

    def test_settings_store__mapping_interface(self):
        """
        Tests that the settings store acts like an immutable mapping.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(
                STR_VAL='foo_upd',
                FLOAT_VAL=6.6,
            )
        with self.assertNumQueries(0):
            self.assertEqual(settings_store['STR_VAL'], 'foo_upd')
            self.assertEqual(settings_store['FLOAT_VAL'], 6.6)
            self.assertEqual(settings_store['DICT_VAL'], {'key': 'value'})
            self.assertEqual(settings_store['LIST_VAL'], [1, 2, 3, 4, 5])
            self.assertEqual(len(settings_store), 4)
            self.assertEqual([k for k in settings_store], ['STR_VAL', 'FLOAT_VAL', 'DICT_VAL', 'LIST_VAL'])
            self.assertEqual(list(settings_store.keys()), ['STR_VAL', 'FLOAT_VAL', 'DICT_VAL', 'LIST_VAL'])
            self.assertEqual(
                list(settings_store.values()),
                ['foo_upd', 6.6, {'key': 'value'}, [1, 2, 3, 4, 5]]
            )
            self.assertEqual(
                list(settings_store.items()),
                [('STR_VAL', 'foo_upd'), ('FLOAT_VAL', 6.6), ('DICT_VAL', {'key': 'value'}), ('LIST_VAL', [1, 2, 3, 4, 5])]
            )
            self.assertTrue('STR_VAL' in settings_store)
            self.assertTrue('FLOAT_VAL' in settings_store)
            self.assertTrue('DICT_VAL' in settings_store)
            self.assertTrue('LIST_VAL' in settings_store)

    def test_settings_store__override(self):
        """
        Tests the settings store's override method.
        """
        settings_store = get_new_setting_store()
        with self.assertNumQueries(7):
            settings_store.update(
                STR_VAL='foo_upd',
                FLOAT_VAL=6.6,
            )
        self.assertEqual(settings_store.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store.FLOAT_VAL, 6.6)

        @settings_store.override(LIST_VAL=[6, 7, 8])
        class Klass:
            @settings_store.override(STR_VAL='foo_over')
            def test_something(_self):
                with settings_store.override(FLOAT_VAL=8.8):
                    settings_store.refresh(full=True)  # no effects on overrides
                    self.assertEqual(settings_store['STR_VAL'], 'foo_over')
                    self.assertEqual(settings_store['FLOAT_VAL'], 8.8)
                    self.assertEqual(settings_store['LIST_VAL'], [6, 7, 8])
                self.assertEqual(settings_store['STR_VAL'], 'foo_over')
                self.assertEqual(settings_store['FLOAT_VAL'], 6.6)
                self.assertEqual(settings_store['LIST_VAL'], [6, 7, 8])

        Klass().test_something()
        self.assertEqual(settings_store.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store.FLOAT_VAL, 6.6)
        self.assertEqual(settings_store.LIST_VAL, [1, 2, 3, 4, 5])

    def test_settings_store__cleanup_settings(self):
        self.assertEqual(SettingsModel.objects.count(), 0)
        SettingsModel.objects.create(key='STR_VAL', value='foo_upd')
        SettingsModel.objects.create(key='FLOAT_VAL', value=6.6)
        SettingsModel.objects.create(key='OBSOLETE', value='obsolete')
        self.assertEqual(SettingsModel.objects.count(), 3)

        settings_store = SettingsStore()
        with self.assertNumQueries(5):
            settings_store.cleanup_settings()
        db_rows = SettingsModel.objects.all()
        self.assertEqual(len(db_rows), 4)
        db_rows = {db_row.key: db_row for db_row in db_rows}
        self.assertEqual(db_rows['STR_VAL'].value, 'foo_upd')
        self.assertEqual(db_rows['FLOAT_VAL'].value, 6.6)
        self.assertEqual(db_rows['DICT_VAL'].value, {'key': 'value'})
        self.assertEqual(db_rows['LIST_VAL'].value, [1, 2, 3, 4, 5])


class SettingsStoreLockTests(TransactionTestCase):
    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    @contextmanager
    def another_connection(self):
        conn = None
        try:
            connections.ensure_defaults('default')
            backend = load_backend(connections.databases['default']['ENGINE'])
            conn = backend.DatabaseWrapper(connections.databases['default'])
            yield conn
        finally:
            if conn:
                conn.close()

    @contextmanager
    def execute_on_another_connection(self):
        with self.another_connection() as conn:
            try:
                prev_conn = connections['default']
                connections['default'] = conn
                yield conn
            finally:
                connections['default'] = prev_conn

    @contextmanager
    def lock_on_another_connection(self, settings_store, *setting_names):
        """
        We actually don't lock in another connection. Instead, we lock this
        connection and swap in a new connection for the context execution.
        The result is the same.
        """
        with settings_store.lock(*setting_names):
            with self.execute_on_another_connection():
                yield

    def lock_key(self, settings_store, *keys, wait_timeout=0):
        with settings_store.lock(*keys, wait_timeout=wait_timeout) as locked:
            self.assertTrue(locked)
        return locked

    def test_settings_store__lock__rows(self):
        settings_store = get_new_setting_store()

        # rows vs. rows
        with self.lock_on_another_connection(settings_store, 'STR_VAL'):
            with self.assertNumQueries(2):
                self.assertTrue(self.lock_key(settings_store, 'FLOAT_VAL', wait_timeout=1))

            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: self.lock_key(settings_store, 'STR_VAL', wait_timeout=1)
                )

        # rows vs. table
        with self.lock_on_another_connection(settings_store):
            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: self.lock_key(settings_store, 'STR_VAL', wait_timeout=1)
                )
            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: self.lock_key(settings_store, 'FLOAT_VAL', wait_timeout=1)
                )

    def test_settings_store__lock__table(self):
        settings_store = get_new_setting_store()

        # table vs. rows
        with self.lock_on_another_connection(settings_store, 'STR_VAL'):
            with self.assertNumQueries(1):
                self.assertRaises(
                    OperationalError,
                    lambda: self.lock_key(settings_store, wait_timeout=1)
                )

        # table vs. table
        with self.lock_on_another_connection(settings_store):
            with self.assertNumQueries(1):
                self.assertRaises(
                    OperationalError,
                    lambda: self.lock_key(settings_store, wait_timeout=1)
                )

    def test_settings_store__lock_for_update(self):
        settings_store = get_new_setting_store()

        # update vs. rows lock
        with self.lock_on_another_connection(settings_store, 'STR_VAL'):
            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: settings_store.update(STR_VAL='foo_upd')
                )

            settings_store.update(FLOAT_VAL=6.6)
            self.assertEqual(settings_store.FLOAT_VAL, 6.6)

        # update vs. table lock
        with self.lock_on_another_connection(settings_store):
            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: settings_store.update(STR_VAL='foo_upd')
                )

            with self.assertNumQueries(2):
                self.assertRaises(
                    OperationalError,
                    lambda: settings_store.update(FLOAT_VAL=6.6)
                )

    def test_settings_store__lost_update_race_condition(self):
        """
        Tests a race condition scenario:
        - Process 1 (p1) starts an update
        - Process 2 (p2) starts and completes an update
        - p2 does a refresh, doesn't see the changes from p1 because not
          committed
        - p1 commits, but because it started first, its version control field
          (VCF) is before p2
        - p2 now only does refresh from its latest known VCF, which is after
          p1's changes and never sees p1's changes

        There are two ways to solve this:
        - lock the whole table on update. Works but heavy-handed solution for a
          small problem. Also makes granular locking impossible and is
          complicated to test.
        - use a SERIALIZABLE transaction with a retry mechanism. Ideal for low
          concurrency writes, doesn't lock the whole table and easier to test.
        """
        settings_store_1 = get_new_setting_store()
        settings_store_2 = get_new_setting_store()
        settings_store_1.cleanup_settings()  # sets up defaults in db
        settings_store_2.cleanup_settings()

        real_bulk_update = SettingsModel.objects.bulk_update

        def do_concurrent_update(*args, **kwargs):
            with mock.patch.object(settings_store_2.model.objects, 'bulk_update', real_bulk_update):
                with self.execute_on_another_connection():
                    settings_store_2.update(FLOAT_VAL=6.6)
            real_bulk_update(*args, **kwargs)

        with mock.patch.object(settings_store_1.model.objects, 'bulk_update', do_concurrent_update):
            settings_store_1.update(STR_VAL='foo_upd')

        settings_store_1.refresh()
        self.assertEqual(settings_store_1.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store_1.FLOAT_VAL, 6.6)
        settings_store_2.refresh()
        self.assertEqual(settings_store_2.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store_2.FLOAT_VAL, 6.6)


class SettingsStoreFormTests(TestCase):
    def setUp(self):
        print('\n\033[96m----- %s.%s -----\033[0m' % (self.__class__.__name__, self._testMethodName))
        super().setUp()

    def test_settings_store_form(self):
        settings_store = get_new_setting_store()
        self.assertEqual(settings_store.STR_VAL, 'foo')
        self.assertEqual(settings_store.FLOAT_VAL, 5.5)

        form = SettingsStoreValForm({'str_val': 'foo_upd', 'float_val': 6.6}, settings_store=settings_store)
        self.assertEqual(form.initial, {'str_val': 'foo', 'float_val': 5.5})
        self.assertEqual(form.Meta.default_values, {'str_val': 'foo', 'float_val': 5.5})
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active in a few seconds.'))

        self.assertEqual(settings_store.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store.FLOAT_VAL, 6.6)

    def test_settings_store_form__initial(self):
        settings_store = get_new_setting_store()
        settings_store.update(STR_VAL='foo_upd', FLOAT_VAL=6.6)
        self.assertEqual(settings_store.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store.FLOAT_VAL, 6.6)

        form = SettingsStoreValForm({'str_val': 'foo_upd_2', 'float_val': 7.7}, settings_store=settings_store)
        self.assertEqual(form.initial, {'str_val': 'foo_upd', 'float_val': 6.6})
        self.assertEqual(form.Meta.default_values, {'str_val': 'foo', 'float_val': 5.5})
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active in a few seconds.'))

        self.assertEqual(settings_store.STR_VAL, 'foo_upd_2')
        self.assertEqual(settings_store.FLOAT_VAL, 7.7)

    @mock.patch('django_web_utils.forms_utils.set_settings')
    def test_settings_store_form__file_settings_form_compat(self, mock_set_settings):
        settings_store = get_new_setting_store()
        self.assertEqual(settings_store.STR_VAL, 'foo')
        self.assertEqual(settings_store.FLOAT_VAL, 5.5)

        form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=settings_store)
        self.assertEqual(form.initial, {'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'})
        self.assertEqual(form.Meta.default_values, {'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'})
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active in a few seconds.'))

        self.assertEqual(settings_store.STR_VAL, 'foo_upd')
        self.assertEqual(settings_store.FLOAT_VAL, 6.6)
        mock_set_settings.assert_called_once_with([('FILE_VAL', 'foo_file_upd')])

    @mock.patch('django_web_utils.forms_utils.set_settings')
    def test_settings_store_form__file_settings_form_compat__success_message_from_file_settings_form(self, mock_set_settings):
        mock_set_settings.return_value = (True, _('Your changes will be active after the service restart.'))

        # No change in SettingsStore -> FileSettingsForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active after the service restart.'))

        # Change in SettingsStore -> SettingsStoreForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active in a few seconds.'))

    @mock.patch('django_web_utils.forms_utils.set_settings')
    def test_settings_store_form__file_settings_form_compat__no_change_from_file_settings_form(self, mock_set_settings):
        mock_set_settings.return_value = (True, _('No changes to save.'))

        # No change in SettingsStore -> SettingsStoreForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('No changes to save.'))

        # Change in SettingsStore -> SettingsStoreForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, True)
        self.assertEqual(msg, _('Your changes will be active in a few seconds.'))

    @mock.patch('django_web_utils.forms_utils.set_settings')
    def test_settings_store_form__file_settings_form_compat__error_from_file_settings_form(self, mock_set_settings):
        mock_set_settings.return_value = (False, _('Unable to write configuration file'))

        # No change in SettingsStore -> FileSettingsForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo', 'float_val': 5.5, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, False)
        self.assertEqual(msg, _('Unable to write configuration file'))

        # Change in SettingsStore -> FileSettingsForm msg is returned
        form = SettingsStoreValFileForm({'str_val': 'foo_upd', 'float_val': 6.6, 'file_val': 'foo_file_upd'}, settings_store=get_new_setting_store())
        success, msg = form.save()
        self.assertEqual(success, False)
        self.assertEqual(msg, _('Unable to write configuration file'))
