#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This scrip outputs the SQL insert commands for an object and all its related objects.
# The related objects are the same as the ones that will be deleted by cascade if the object is deleted.
# Author: Stéphane Diemer stephane.diemer@ubicast.eu
import os
import sys
import datetime
from decimal import Decimal
os.environ['LANG'] = 'en_US.UTF-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'
reload(sys)  # reload sys to make setdefaultencoding available
sys.setdefaultencoding('utf-8')

SETTINGS_MODULE = 'settings'


def get_related_data(model, model_id):
    # Fill python path
    base_dir = os.getcwd()
    if base_dir not in sys.path:
        sys.path.append(base_dir)
    if os.path.dirname(base_dir) not in sys.path:
        sys.path.append(os.path.dirname(base_dir))
    # Setup Django
    if not os.environ.get('DJANGO_SETTINGS_MODULE') or os.environ.get('DJANGO_SETTINGS_MODULE') != SETTINGS_MODULE:
        # if the DJANGO_SETTINGS_MODULE is already set,
        # the logging will not be changed to avoid possible
        # impact on the server which called this script.
        os.environ['DJANGO_SETTINGS_MODULE'] = SETTINGS_MODULE
    import django
    try:
        django.setup()
    except Exception:
        pass
    # Get model
    if '.' in model:
        element = model.split('.')[-1]
        _tmp = __import__(model[:-len(element) - 1], fromlist=[element])
        model_class = getattr(_tmp, element)
    else:
        model_class = __import__(model)
    # Get object
    main_obj = model_class.objects.get(id=model_id)
    # Collect models
    from django.contrib.admin import utils
    collector = utils.NestedObjects(using='default')
    collector.collect([main_obj])
    objs = list()
    collector.nested(lambda obj: objs.append(obj))
    # Prepare insert query
    sql = 'BEGIN;\n'
    for obj in objs:
        fields = ','.join(['`%s`' % f.column for f in obj.__class__._meta.fields])
        values = ','.join([_get_sql_val(obj, f) for f in obj.__class__._meta.fields])
        line = 'INSERT INTO `%s` (%s) VALUES (%s);' % (obj.__class__._meta.db_table, fields, values)
        sql += line + '\n'
    sql += 'COMMIT;'
    return sql


def _get_sql_val(obj, field):
    val = getattr(obj, field.column)
    if val is None:
        if not field.null:
            print('Error: Object %s with id %s: The field %s is NULL and cannot be!' % (obj.__class__.__name__, obj.id, field.column), file=sys.stderr)
        return 'NULL'
    elif isinstance(val, bool):
        return '1' if val else '0'
    elif isinstance(val, (int, float, Decimal)):
        return str(val)
    elif isinstance(val, datetime.datetime):
        val = val.strftime('%Y-%m-%d')
    elif isinstance(val, datetime.date):
        val = val.strftime('%Y-%m-%d %H:%M:%S')
    else:
        if hasattr(val, 'name'):
            val = val.name
        if not val:
            val = ''
        val = val.replace('\'', '\\\'')
    return '\'%s\'' % val


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Not enough arguments.\nTwo arguments are required: model python path and model id.\nExample: %s myapp.models.Test 25' % __file__, file=sys.stderr)
        sys.exit(1)
    sql = get_related_data(*sys.argv[1:])
    print(sql, file=sys.stdout)
