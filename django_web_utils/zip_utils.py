#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Zip utility functions
'''
import os
import zipfile
# Django
from mediaserver import shared


# _add_to_zip function
# internal function
#-----------------------------------------------------------------------------------
def _add_to_zip(zip_file, path, ignored=None, path_in_zip=None):
    for name in os.listdir(path):
        if ignored and name in ignored:
            continue
        picked_path = os.path.join(path, name)
        picked_path_in_zip = path_in_zip + '/' + name if path_in_zip else name
        if os.path.isfile(picked_path):
            zip_file.write(picked_path.encode('ascii'), picked_path_in_zip.encode('ascii'))
        elif os.path.isdir(picked_path):
            _add_to_zip(zip_file, picked_path, ignored, picked_path_in_zip)

# create_zip function
#-----------------------------------------------------------------------------------
def create_zip(path, zip_path, ignored=None, prefix=None):
    if not os.path.exists(os.path.dirname(zip_path)):
        os.makedirs(os.path.dirname(zip_path))
    
    zip_file = zipfile.ZipFile(zip_path, 'w')
    try:
        _add_to_zip(zip_file, path, ignored, path_in_zip=prefix)
    except Exception:
        zip_file.close()
        if os.path.exists(zip_path):
            os.remove(zip_path)
    else:
        zip_file.close()

# unzip function
#-----------------------------------------------------------------------------------
def unzip(path, zip_path=None, zip_file=None):
    if zip_file:
        used_zip_file = zip_file
    else:
        # open zip file
        if not zip_path:
            return shared.Result(success=False, message='No zip file specified.')
        try:
            used_zip_file = zipfile.ZipFile(zip_path, 'r')
        except Exception, e:
            return shared.Result(success=False, message='Cannot open zip file (%s). Error: %s.' %(zip_path, e))
    try:
        # CRC test
        zip_test = used_zip_file.testzip()
        if zip_test:
            return shared.Result(success=False, message='CRC error on zip file. Error detected on: %s' %zip_test)
        # create destination path
        if not os.path.exists(os.path.dirname(path)):
            try:
                os.makedirs(os.path.dirname(path))
            except Exception, e:
                return shared.Result(success=False, message='Cannot create folder "%s". Error is: %s' %(path, e))
        # extract files
        used_zip_file.extractall(path)
        return shared.Result(success=True)
    except AttributeError:
        # for python 2.5
        os.system('unzip -d %s %s' %(path, zip_path))
        return shared.Result(success=True)
    except Exception:
        return shared.Result(success=False, message='File is not a valid zip.')
    finally:
        if not zip_file:
            used_zip_file.close()

