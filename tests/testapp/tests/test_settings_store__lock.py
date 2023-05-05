from contextlib import contextmanager
from unittest import mock

import pytest
from django.db import connections
from django.db.utils import load_backend, OperationalError

from testapp.models import SettingsModel

from .test_settings_store__api import get_new_setting_store

pytestmark = pytest.mark.django_db(transaction=True)


@contextmanager
def another_connection():
    conn = None
    try:
        backend = load_backend(connections.databases['default']['ENGINE'])
        conn = backend.DatabaseWrapper(connections.databases['default'])
        yield conn
    finally:
        if conn:
            conn.close()


@contextmanager
def execute_on_another_connection():
    with another_connection() as conn:
        try:
            prev_conn = connections['default']
            connections['default'] = conn
            yield conn
        finally:
            connections['default'] = prev_conn


@contextmanager
def lock_on_another_connection(settings_store, *setting_names):
    """
    We actually don't lock in another connection. Instead, we lock this
    connection and swap in a new connection for the context execution.
    The result is the same.
    """
    with settings_store.lock(*setting_names):
        with execute_on_another_connection():
            yield


def lock_key(settings_store, *keys, wait_timeout=0):
    with settings_store.lock(*keys, wait_timeout=wait_timeout) as locked:
        assert locked is True
    return locked


def test_settings_store__lock__rows(django_assert_num_queries):
    settings_store = get_new_setting_store()

    # rows vs. rows
    with lock_on_another_connection(settings_store, 'STR_VAL'):
        with django_assert_num_queries(4):
            assert lock_key(settings_store, 'FLOAT_VAL', wait_timeout=1) is True

        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                lock_key(settings_store, 'STR_VAL', wait_timeout=1)

    # rows vs. table
    with lock_on_another_connection(settings_store):
        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                lock_key(settings_store, 'STR_VAL', wait_timeout=1)
        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                lock_key(settings_store, 'FLOAT_VAL', wait_timeout=1)


def test_settings_store__lock__table(django_assert_num_queries):
    settings_store = get_new_setting_store()

    # table vs. rows
    with lock_on_another_connection(settings_store, 'STR_VAL'):
        with django_assert_num_queries(3):
            with pytest.raises(OperationalError):
                lock_key(settings_store, wait_timeout=1)

    # table vs. table
    with lock_on_another_connection(settings_store):
        with django_assert_num_queries(3):
            with pytest.raises(OperationalError):
                lock_key(settings_store, wait_timeout=1)


def test_settings_store__lock_for_update(django_assert_num_queries):
    settings_store = get_new_setting_store()

    # update vs. rows lock
    with lock_on_another_connection(settings_store, 'STR_VAL'):
        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                settings_store.update(STR_VAL='foo_upd')

        settings_store.update(FLOAT_VAL=6.6)
        assert settings_store.FLOAT_VAL == 6.6

    # update vs. table lock
    with lock_on_another_connection(settings_store):
        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                settings_store.update(STR_VAL='foo_upd')

        with django_assert_num_queries(4):
            with pytest.raises(OperationalError):
                settings_store.update(FLOAT_VAL=6.6)


def test_settings_store__lost_update_race_condition():
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
            with execute_on_another_connection():
                settings_store_2.update(FLOAT_VAL=6.6)
        real_bulk_update(*args, **kwargs)

    with mock.patch.object(settings_store_1.model.objects, 'bulk_update', do_concurrent_update):
        settings_store_1.update(STR_VAL='foo_upd')

    settings_store_1.refresh()
    assert settings_store_1.STR_VAL == 'foo_upd'
    assert settings_store_1.FLOAT_VAL == 6.6
    settings_store_2.refresh()
    assert settings_store_2.STR_VAL == 'foo_upd'
    assert settings_store_2.FLOAT_VAL == 6.6


@contextmanager
def _check_applied_timeout(expected_timeout):
    with mock.patch('django_web_utils.settings_store.store.connection') as mock_conn:
        mock_execute = mock_conn.cursor.return_value.__enter__.return_value.execute
        yield mock_execute
        if expected_timeout is None:
            mock_execute.assert_not_called()
        else:
            mock_execute.assert_called_once()
            sql = mock_execute.call_args[0][0]
            if expected_timeout >= 1:
                assert f"SET LOCAL lock_timeout = '{expected_timeout}ms';" in sql
            else:
                assert "SET LOCAL lock_timeout = '1ms';" in sql


def test_settings_store__lock_timeout_override():
    settings_store = get_new_setting_store(default_lock_timeout=None)
    with _check_applied_timeout(expected_timeout=None):
        settings_store.update(STR_VAL='foo_upd')
    with _check_applied_timeout(expected_timeout=100):
        settings_store.update(STR_VAL='foo_upd', wait_timeout=100)

    settings_store = get_new_setting_store(default_lock_timeout=100)
    with _check_applied_timeout(expected_timeout=100):
        settings_store.update(STR_VAL='foo_upd')
    with _check_applied_timeout(expected_timeout=200):
        settings_store.update(STR_VAL='foo_upd', wait_timeout=200)

    settings_store = get_new_setting_store(default_lock_timeout=200)
    with _check_applied_timeout(expected_timeout=200):
        settings_store.update(STR_VAL='foo_upd')
    with _check_applied_timeout(expected_timeout=100):
        settings_store.update(STR_VAL='foo_upd', wait_timeout=100)
