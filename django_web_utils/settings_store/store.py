from __future__ import annotations

import datetime
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from typing import Optional, Type, TYPE_CHECKING
from unittest import mock

# Django
from django.db import connection, transaction
from django.utils.module_loading import import_string

if TYPE_CHECKING:
    from .models import AbstractSettingsModel


class InvalidSetting(Exception):
    pass


class SettingsStoreBase(Mapping):
    """
    Frozen base-class for managing settings in the database (e.g.: admin
    settings that the client can change while the server is running).

    Implements `collections.Mapping`, so subclasses will have immutable mapping
    methods and behavior.

    Thread-safety not included (but trivial to implement on top).

    TL;DR: skip to the "Usage" section.

    Settings are saved in the database in a key-value table (1 setting = 1 row).
    Even if you don't need to add anything to the model, you must create
    subclasses for both `AbstractSettingsModel` and this class and pass your
    concrete model as a kwarg to this subclass definition (cf. "Usage").

    Settings are lazy-loaded: on the first attribute access, all settings are
    queried from the database. Every attribute access after the first one will
    be free (no database request).

    To refresh a stale settings collection, call `.refresh()` on it. Only
    settings that have been updated since the last refresh will be queried to
    keep the query's cost minimal. A `cache_ttl` can be set at instantation to
    prevent more than one refresh every `cache_ttl` seconds.

    To commit settings updates to the database, use `.update(**kw)`. If you need
    a temporary override (in tests, for instance), use the `.override(**kw)`
    contextmanager/decorator. Either way, don't try to `setattr` directly on
    the class as it is frozen: it will raise.

    Settings should be defined as class-level attributes on a subclass of this
    base-class. By default, for attributes to be considered valid settings
    (i.e.: to pass basic validation for an update/override), they must:
        - point to non-callable values,
        - be public (no leading underscore),
        - be all-uppercase.
    If you need a different behavior, you must provide your own override of
    `._is_setting_name(cls, name)`. It should return a boolean value.

    When you change the attribute on the class, don't forget to call
    `.cleanup_settings()` in a migration. This ensures that default values are
    always in the database so locking always works. You'll get an error on the
    `.update()` if you forget.

    Should your subclass need to provide additional validation, override the
    `._validate(**kw)` method. It should not need to be called by user code,
    though it will be called automatically before an update/override call.

    All values must be JSON serializable or the `.update()` method will raise.
    The alternative is to set a custom serializer on the model's `.values`.

    Usage
    ::
        >>> class MyConcreteModel(AbstractSettingsModel):
        ...     pass

        >>> class MySettings(SettingsStoreBase, model=MyConcreteModel):
        ...     FOO: str = 'foo'
        ...     BAR: str = 'bar'
        ...     BAZ: str = 'baz_def'

        >>> settings = MySettings()  # no database query
        >>> print(settings.FOO)  # 1 database query
        'foo'
        >>> print(settings.BAR)  # no database query
        'bar'
        >>> settings.refresh() # 1 minimal database query
        >>> settings.update(
        ...     FOO='foo_up', BAR='bar_up', BAZ='baz'
        ... )  # 1 SELECT FOR UPDATE (FOO + BAR)
        ...    # 1 bulk UPDATE (FOO + BAR)
        ...    # 1 bulk INSERT (BAZ)
        ...    # 1 minimal SELECT (refresh)
        >>> print(settings.FOO)  # no database query
        'foo'
        >>> print(settings.BAR)  # no database query
        'bar'
        >>> print(settings.BAZ)  # no database query
        'baz'

        >>> @settings.override(FOO='foo_over')
        ... def test_something():
        ...     with settings.override(BAR='bar_over'):
        ...         assert settings['FOO'] = 'foo_over'
        ...         assert settings['BAR'] = 'bar_over'
    """

    # Define settings fields (name[: type] = default_value) here:
    # FOO: str = 'foo'

    # INIT
    def __init_subclass__(cls, model: Type[AbstractSettingsModel] = None):
        cls._model = model
        cls._validate_model(lazy=True)
        cls._defaults: dict = cls._get_defaults()

    def __init__(self, cache_ttl: int = 0):
        # Initialize a per-instance internal mapping with default values
        self._mapping: dict = deepcopy(self._defaults)
        self._last_updated_at: Optional[datetime.datetime] = None
        self._last_refreshed_at: Optional[datetime.datetime] = None
        self._cache_ttl = cache_ttl
        self._no_lock_timeout = False  # Use in tests to avoid random timeout errors.

    # GET/SET
    def __getattribute__(self, name):
        """
        Redirect access to settings via attributes to internal `._mapping`.
        """
        if name in object.__getattribute__(self, '_defaults'):
            return self.__getitem__(name)
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Prevent writing attributes directly if they are settings."""
        if name in self._defaults:
            cls_name = self.__class__.__name__
            raise TypeError(
                f'{cls_name} is frozen by design. Use `{cls_name}.update(**kw)` '
                f'to update multiple values at once or the {cls_name}.override('
                f'**kw) contextmanager/decorator for a temporary override.'
            )
        return object.__setattr__(self, name, value)

    # MAPPING INTERFACE
    def __getitem__(self, item):
        if self._last_refreshed_at is None and item in self._mapping:
            self.refresh()
        return self._mapping[item]

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return f'{super().__repr__()}: {str(self)}'

    def __str__(self):
        return str(self._mapping)

    # DEFAULTS
    @classmethod
    def _is_setting_name(cls, name):
        return (
            not name.startswith('_')
            and name.isupper()
            and not callable(getattr(cls, name))
        )

    @classmethod
    def _get_defaults(cls):
        super_get_defaults = getattr(super(), '_get_defaults', None)
        if super_get_defaults:
            defaults = {k: v for k, v in super_get_defaults()}
        else:
            defaults = {}

        for attr_name in cls.__dict__.keys():
            if cls._is_setting_name(attr_name):
                defaults[attr_name] = getattr(cls, attr_name)
        return defaults

    @classmethod
    def get_default(cls, setting_name):
        return cls._defaults[setting_name]

    # VALIDATION
    def _validate_names(self, *setting_names):
        """Validates setting names against our list of settings."""
        unknown_keys = set(setting_names).difference(self._mapping.keys())
        if unknown_keys:
            raise InvalidSetting(
                f'These keys are unknown: {unknown_keys}. This can be the '
                f'result of a misspelling or you forgot to add the keys to '
                f'the {self.__class__.__name__} class.'
            )

    def _validate(self, **settings):
        """
        Override this method to set up custom data validation. Validation is
        performed automatically before an update / override. There is no need
        for user code to call this method directly.
        """
        pass

    # DATABASE INTERFACE
    @classmethod
    def _validate_model(cls, lazy=False):
        if cls._model and isinstance(cls._model, str):
            if lazy is True:
                return cls._model
            else:
                cls._model = import_string(cls._model)

        from django_web_utils.settings_store.models import AbstractSettingsModel
        if (
            cls._model
            and issubclass(cls._model, AbstractSettingsModel)
            and not cls._model._meta.abstract
        ):
            return cls._model

        raise TypeError(
            f'Cannot instantiate {cls.__name__}. A concrete database model '
            f'must be provided as a keyword argument to {cls.__name__}\'s '
            f'definition (e.g.: class {cls.__name__}(SettingsStoreBase, '
            f'model="path.to.MyConcreteModel"): ...).'
        )

    @property
    def model(self) -> Type[AbstractSettingsModel]:
        return self._validate_model(lazy=False)

    def refresh(self, force=False, full=False):
        """
        Refresh settings with values from the database.

        :param force: perform the refresh even if cache_ttl hasn't expired.
        :param full: refresh all settings regardless of when they were last
                     updated.
        :return: None
        """
        if (
            not force
            and self._last_refreshed_at is not None
            and self._cache_ttl > 0
            and datetime.datetime.now() - self._last_refreshed_at <= datetime.timedelta(seconds=self._cache_ttl)
        ):
            return

        now = datetime.datetime.now()
        mapping = self._mapping

        qs = self.model.objects.values_list('key', 'value', 'updated_at')
        if not full and self._last_updated_at is not None:
            qs = qs.filter(updated_at__gt=self._last_updated_at)

        refreshed = []
        for key, value, updated_at in qs.all():
            # If obsolete settings are still in the database, ignore them.
            if key not in mapping:
                continue

            mapping[key] = value
            refreshed.append(key)
            if self._last_updated_at is None or self._last_updated_at < updated_at:
                object.__setattr__(self, '_last_updated_at', updated_at)

        object.__setattr__(self, '_last_refreshed_at', now)
        return refreshed

    @contextmanager
    def _lock(self, *setting_names, wait_timeout: int = 100):
        wait_timeout = max(1, int(wait_timeout))

        if setting_names:
            self._validate_names(*setting_names)
            with transaction.atomic():
                if not self._no_lock_timeout:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"SET LOCAL lock_timeout = '{wait_timeout}ms';"
                        )
                yield list(
                    self.model.objects.select_for_update(nowait=False).filter(
                        key__in=setting_names
                    )
                )
        else:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    stmt = ''
                    if not self._no_lock_timeout:
                        stmt += f"SET LOCAL lock_timeout = '{wait_timeout}ms';"
                    stmt += f'LOCK TABLE {self.model._meta.db_table} IN EXCLUSIVE MODE;'
                    cursor.execute(stmt)
                yield

    @contextmanager
    def lock(self, *setting_names, wait_timeout: int = 100):
        """
        Lock specific settings or all settings. Locks are transaction-bound.
        This means the call to this function must be done within a transaction
        block (`transaction.atomic`). Also, there is no need to manually
        release these locks. They are automatically released at the end of the
        transaction (`COMMIT`, `ROLLBACK`, connection lost...).

        :param setting_names: name of the settings to lock. If none are passed,
                              all settings will be locked.
        :param wait_timeout: pass a wait timeout (in milliseconds) for the lock.
                             If the lock cannot be acquired in time, an
                             OperationalError will be raised.
        :return: True when the lock is acquired.
        """
        with self._lock(*setting_names, wait_timeout=wait_timeout):
            yield True

    def update(self, **updates):
        """
        Updates settings in the database.

        :param updates: key/value mapping of settings to update.
        :return: None
        """
        if not updates:
            return

        update_keys = list(updates.keys())
        self._validate_names(*update_keys)

        # Upsert the keys into the database.
        with self._lock(*update_keys, wait_timeout=100) as db_models:
            # TODO: When Django brings support for Postgres' upsert statement
            #       (INSERT... ON CONFLICT...), these 3 queries should be
            #       replaced with one upsert using the unique index on `key` as
            #       a discriminant. Expected in Django 4.1:
            #       https://docs.djangoproject.com/en/dev/releases/4.1/#models
            updated_at = datetime.datetime.now()
            for db_model in db_models:
                updated_value = updates.pop(db_model.key)
                if callable(updated_value):
                    updated_value = updated_value(db_model.value)
                db_model.value = updated_value
                db_model.updated_at = updated_at

            self._validate(**{db_model.key: db_model.value for db_model in db_models})

            self.model.objects.bulk_update(
                db_models,
                fields=('value', 'updated_at'),
                batch_size=len(db_models),
            )

            # Any leftover updates don't exist in the db yet. This is an error.
            if updates:
                raise RuntimeError(
                    f'These keys are not in the database: {list(updates.keys())}. '
                    f'Did you forget to call `.cleanup_settings()` in a migration?'
                )

        # Re-stamp the updated keys with a post-commit datetime, to ensure we
        # don't get into the "lost update" scenario (see tests). This technique
        # is the most lightweight, as it doesn't require explicit locking of
        # the whole table or using serializable transactions.
        now = datetime.datetime.now()
        self.model.objects.filter(key__in=update_keys).update(updated_at=now)
        self.refresh(force=True)

    def cleanup_settings(self):
        """
        Puts the default values in the database if they don't exist (so
        `.lock()` works on them) and deletes settings from the database if they
        are not in the class' definition.
        """
        with transaction.atomic():
            self.lock()

            # Insert defaults
            # TODO: replace with upsert when Django 4.1 is released.
            keys_in_db = list(self.model.objects.values_list('key', flat=True))
            updated_at = datetime.datetime.now()
            self.model.objects.bulk_create(
                [
                    self.model(key=key, value=value, updated_at=updated_at)
                    for key, value in self._defaults.items()
                    if key not in keys_in_db
                ],
                batch_size=len(self._defaults),
            )

            # Delete obsolete keys
            self.model.objects.exclude(key__in=self._mapping.keys()).delete()

    # TEST-SUITE HELPERS
    def override(self, **overrides):
        """
        Context manager / decorator to temporarily modify settings (nothing is
        committed to the database):

        Usage (with settings being an instance of this class)::

            @settings.override(FOO='foo_over')
            def test_something():
                with settings.override(BAR='bar_over'):
                    assert settings['FOO'] == 'foo_over'
                    assert settings['BAR'] == 'bar_over'
        """
        return Patcher(self, **overrides)


class Patcher:
    def __init__(self, setting_store, **overrides):
        self._setting_store = setting_store
        self._overrides = overrides
        self._current_values = {}

    def __call__(self, func):
        if isinstance(func, type):
            return self._decorate_class(func)
        return self._decorate_callable(func)

    def _decorate_class(self, klass):
        for attr in dir(klass):
            if not attr.startswith(mock.patch.TEST_PREFIX):
                continue
            attr_value = getattr(klass, attr)
            if not hasattr(attr_value, "__call__"):
                continue

            setattr(klass, attr, self(attr_value))
        return klass

    def _decorate_callable(self, func):
        @wraps(func)
        def patched(*args, **kwargs):
            with Patcher(self._setting_store, **self._overrides):
                func(*args, **kwargs)
        return patched

    def __enter__(self):
        self._setting_store.refresh(force=True)
        self._current_values = {
            k: self._setting_store[k]
            for k in self._overrides.keys()
        }
        self._setting_store.update(**self._overrides)

    def __exit__(self, *args):
        self._setting_store.update(**self._current_values)
        return False
