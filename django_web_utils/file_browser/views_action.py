#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import errno
import shutil
import unicodedata
import re
# Django
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
# Django web utils
from django_web_utils import json_utils
from django_web_utils.file_browser import config


def force_decode(string, codecs=None):
    if not codecs:
        codecs = ('utf8', 'ascii', 'cp1252')
    # cp1252 is used under windows
    for c in codecs:
        try:
            return string.decode(c)
        except:
            pass
    # if no coded can decode string, return it in unicode
    # (special caracters will be lost)
    return unicode(string, 'utf-8', errors='ignore')


def recursive_remove(path):
    files_deleted = 0
    dir_deleted = 0
    if not os.path.exists(path):
        return files_deleted, dir_deleted
    if os.path.isdir(path):
        for f in os.listdir(path):
            fd, dd = recursive_remove(os.path.join(path, f))
            files_deleted += fd
            dir_deleted += dd
        os.rmdir(path)
        dir_deleted += 1
    elif os.path.isfile(path):
        os.remove(path)
        files_deleted += 1
    return files_deleted, dir_deleted


def clean_file_name(name):
    """ This function is like the slugify function of Django, but it allow points and uppercase lettrs """
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub('[^\.\w\s-]', '', name).strip()
    name = re.sub('[-\s]+', '-', name)
    return name


# storage_action
# ----------------------------------------------------------------------------
@config.view_decorator
def storage_action(request):
    if request.method != 'POST':
        return json_utils.failure_response(message=unicode(_('Invalid request method.')), code=405)

    base_path = config.BASE_PATH
    action = request.POST.get('action')
    # upload form
    if action == 'upload' or action == 'upload-old':
        # check data
        path = request.POST.get('path', '')
        if '..' in path:
            msg = unicode(_('Invalid base path.'))
            if action == 'upload-old':
                messages.error(request, msg)
                return HttpResponseRedirect('%s#%s' % (reverse('file_browser_base'), path))
            else:
                return json_utils.failure_response(message=msg)
        if not request.FILES.keys():
            msg = unicode(_('No files in request.'))
            if action == 'upload-old':
                messages.error(request, msg)
                return HttpResponseRedirect('%s#%s' % (reverse('file_browser_base'), path))
            else:
                return json_utils.failure_response(message=msg)
        if path:
            dir_path = os.path.join(settings.MEDIA_ROOT, 'downloads', path)
        else:
            dir_path = os.path.join(settings.MEDIA_ROOT, 'downloads')
        # create upload folder
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except Exception, e:
                msg = unicode(_('Failed to create dir.'))
                if action == 'upload-old':
                    messages.error(request, msg)
                    return HttpResponseRedirect('%s#%s' % (reverse('file_browser_base'), path))
                else:
                    return json_utils.failure_response(message=msg)
        # execute action
        if len(request.FILES.keys()) == 1:
            msg = unicode(_('The file has been uploaded and is available at the location:'))
        else:
            msg = unicode(_('The files have been uploaded and are available at the locations:'))
        for uploaded_file in request.FILES.values():
            if '.' in uploaded_file.name:
                splitted = uploaded_file.name.split('.')
                file_name = clean_file_name('.'.join(splitted[:-1])) + '.' + clean_file_name(splitted[-1])
            else:
                file_name = clean_file_name(uploaded_file.name)
            # write uploaded file
            f = open(os.path.join(dir_path, file_name), 'wb+')
            for chunk in uploaded_file.chunks():
                f.write(chunk)
            f.close()
            # get url
            if path:
                url = reverse('media', args=[os.path.join('downloads', path, file_name)])
            else:
                url = reverse('media', args=[os.path.join('downloads', file_name)])
            msg += u' <br/><a href="%s">%s://%s%s</a>' % (url, 'https' if request.is_secure() else 'http', request.get_host(), url)
        if action == 'upload-old':
            messages.success(request, msg)
            return HttpResponseRedirect('%s#%s' % (reverse('file_browser_base'), path))
        else:
            return json_utils.success_response(message=msg)

    # folder form
    elif action == 'add_folder':
        # check data
        path = request.POST.get('path', '')
        if '..' in path:
            return json_utils.failure_response(message=unicode(_('Invalid base path.')))
        name = request.POST.get('name')
        if not name:
            return json_utils.failure_response(message=unicode(_('The name field is required.')))
        name = clean_file_name(name)
        if not name:
            return json_utils.failure_response(message=unicode(_('Invalid name.')))
        # execute action
        if path:
            target = os.path.join(settings.MEDIA_ROOT, 'downloads', path, name)
        else:
            target = os.path.join(settings.MEDIA_ROOT, 'downloads', name)
        try:
            os.makedirs(target)
        except OSError, e:
            if e.errno == errno.EEXIST:
                return json_utils.success_response(message=unicode(_('Folder already exists.')))
            else:
                return json_utils.failure_response(message=u'%s %s' % (_('Failed to create dir.'), e))
        return json_utils.success_response(message=unicode(_('Folder created.')))

    # search form
    elif action == 'search':
        # get path
        path = request.REQUEST.get('path', '')
        base_path = os.path.join(settings.MEDIA_ROOT, 'downloads')
        if '..' in path:
            return json_utils.failure_response(message=unicode(_('Invalid base path.')))
        if path:
            dir_path = os.path.join(base_path, path)
        else:
            dir_path = base_path
        if not os.path.exists(dir_path):
            return json_utils.failure_response(message=unicode(_('Requested path does not exist.')))
        # get search command
        search = request.REQUEST.get('search', '')
        search = search.replace('\'', '"').lower()

        dirs = dict()
        results = 0
        for bpath, subdirs, files in os.walk(dir_path):
            for name in subdirs:
                name = force_decode(name)
                if search in name.lower():
                    dir_url = os.path.join(bpath, name)[len(base_path):].replace('\\', '/')
                    if dir_url:
                        if dir_url.startswith('/'):
                            dir_url = dir_url[1:]
                        if not dir_url.endswith('/'):
                            dir_url += '/'
                    dirs[dir_url] = list()
                    results += 1
            for name in files:
                name = force_decode(name)
                if search in name.lower():
                    dir_url = bpath[len(base_path):].replace('\\', '/')
                    if dir_url:
                        if dir_url.startswith('/'):
                            dir_url = dir_url[1:]
                        if not dir_url.endswith('/'):
                            dir_url += '/'
                    if dir_url not in dirs:
                        dirs[dir_url] = list()
                    dirs[dir_url].append(name)
                    results += 1
        urls = dirs.keys()
        urls.sort()
        dirs = [dict(url=url, files=dirs[url]) for url in urls]

        if dirs:
            if path:
                msg = _(u'%(count)s results for "%(search)s" in "%(path)s".') % dict(count=results, search=search, path=path)
            else:
                msg = _(u'%(count)s results for "%(search)s".') % dict(count=results, search=search)
        else:
            msg = _('No results for "%(search)s".') % dict(search=search)

        return json_utils.success_response(search_in=path, msg=unicode(msg), results=results, dirs=dirs)

    # actions on several files form
    elif action in ('rename', 'move', 'delete'):
        # check data
        path = request.POST.get('path', '')
        if '..' in path:
            return json_utils.failure_response(message=unicode(_('Invalid base path.')))
        if path:
            dir_path = os.path.join(settings.MEDIA_ROOT, 'downloads', path)
        else:
            dir_path = os.path.join(settings.MEDIA_ROOT, 'downloads')
        names = list()
        for key in request.POST:
            if key.startswith('name_') and request.POST[key]:
                names.append(request.POST[key])
        if not names:
            return json_utils.failure_response(message=unicode(_('No files selected.')))

        if action == 'rename':
            new_name = request.POST.get('new_name')
            if not new_name:
                return json_utils.failure_response(message=unicode(_('The name field is required.')))
            new_name = clean_file_name(new_name)
            if '.' in new_name:
                splitted = new_name.split('.')
                new_name = clean_file_name('.'.join(splitted[:-1]))
                new_name_ext = '.' + clean_file_name(splitted[-1])
            else:
                new_name = clean_file_name(new_name)
                new_name_ext = ''
            if not new_name:
                return json_utils.failure_response(message=unicode(_('Invalid name.')))
            # execute action
            index = 0
            for name in names:
                src = os.path.join(dir_path, name)
                if len(names) == 1:
                    new = '%s%s' % (new_name, new_name_ext)
                else:
                    index += 1
                    new = '%s-%s%s' % (new_name, index, new_name_ext)
                dest = os.path.join(dir_path, new)
                if src != dest:
                    if os.path.exists(dest):
                        return json_utils.failure_response(message=unicode(_('The file "%s" already exists.')) % new)
                    os.rename(src, dest)
            if len(names) == 1:
                return json_utils.success_response(message=unicode(_('File renamed.')))
            else:
                return json_utils.success_response(message=unicode(_('Files renamed.')))

        elif action == 'move':
            new_path = request.POST.get('new_path', '')
            if not new_path:
                return json_utils.failure_response(message=unicode(_('No path specfied to move files in.')))
            if new_path == '#':
                new_path = base_path
            else:
                new_path = os.path.join(base_path, new_path)
            if not os.path.exists(new_path):
                return json_utils.failure_response(message=unicode(_('Destination path does not exists.')))
            moved = 0
            for name in names:
                src = os.path.join(dir_path, name)
                if src != new_path and not (os.path.isfile(src) and os.path.dirname(src) == new_path):
                    try:
                        shutil.move(src, new_path)
                        moved += 1
                    except Exception, e:
                        return json_utils.failure_response(message=u'%s %s' % (_('Unable to move file %s:') % name, e))
            return json_utils.success_response(message=unicode(_('%s file(s) successfully moved.') % moved))

        else:  # delete
            files_deleted = 0
            dir_deleted = 0
            for name in names:
                if not name:
                    continue
                src = os.path.join(dir_path, name)
                try:
                    fd, dd = recursive_remove(src)
                    files_deleted += fd
                    dir_deleted += dd
                except Exception, e:
                    return json_utils.failure_response(message=u'%s %s' % (_('Unable to delete file %s:') % name, e))
            return json_utils.success_response(message=unicode(_('%(f)s file(s) and %(d)s directory(ies) successfully deleted.') % dict(f=files_deleted, d=dir_deleted)))

    return json_utils.failure_response(message=unicode(_('Unknown action.')))
