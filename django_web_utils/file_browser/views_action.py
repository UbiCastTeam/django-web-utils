#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import shutil
import unicodedata
# Django
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
# Django web utils
from django_web_utils.antivirus_utils import antivirus_file_validator
from django_web_utils.file_browser import config


def recursive_remove(path):
    '''
    Function to remove a dir and all its file.
    Returns the number of deleted files and dirs.
    '''
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
    '''
    This function is like the slugify function of Django,
    but it allows points and uppercase letters.
    '''
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r'[^\.\w\s-]', '', name).strip()
    name = re.sub(r'[-\s]+', '-', name)
    return name


@config.view_decorator
def storage_action(request, namespace=None):
    '''
    Storage action view.
    '''
    base_path = config.get_base_path(namespace)
    if not base_path:
        return JsonResponse(dict(error=_('No base path defined in configuration.')), status=400)
    base_url = config.get_base_url(namespace)
    if not base_url:
        return JsonResponse(dict(error=_('No base url defined in configuration.')), status=400)
    if request.method == 'POST':
        # Actions using post method
        action = request.POST.get('action')
        # Upload form
        if action == 'upload' or action == 'upload_single':
            red_url = None
            if action == 'upload_single':
                if namespace:
                    red_url = reverse('%s:file_browser_base' % namespace)
                else:
                    red_url = reverse('file_browser_base')
            # Check data
            path = request.POST.get('path', '').strip('/')
            if '..' in path:
                msg = _('Invalid base path.')
                if action == 'upload_single':
                    messages.error(request, msg)
                    return HttpResponseRedirect('%s#/%s' % (red_url, path))
                else:
                    return JsonResponse(dict(error=msg), status=400)
            if not list(request.FILES.keys()):
                msg = _('No files in request.')
                if action == 'upload_single':
                    messages.error(request, msg)
                    return HttpResponseRedirect('%s#/%s' % (red_url, path))
                else:
                    return JsonResponse(dict(error=msg), status=400)
            if path:
                dir_path = os.path.join(base_path, path)
            else:
                dir_path = base_path
            dir_path = dir_path
            # Create upload folder
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception as e:
                msg = '%s %s' % (_('Failed to create folder:'), e)
                if action == 'upload_single':
                    messages.error(request, msg)
                    return HttpResponseRedirect('%s#/%s' % (red_url, path))
                else:
                    return JsonResponse(dict(error=msg), status=400)
            # Execute action
            if len(list(request.FILES.keys())) == 1:
                msg = _('The file has been uploaded and is available at the location:')
            else:
                msg = _('The files have been uploaded and are available at the locations:')
            urls = list()
            for uploaded_file in list(request.FILES.values()):
                file_name = clean_file_name(uploaded_file.name)
                if file_name == '.htaccess':
                    file_name += '_'
                # Write uploaded file
                file_path = os.path.join(dir_path, file_name)
                with open(file_path, 'wb+') as fo:
                    for chunk in uploaded_file.chunks():
                        fo.write(chunk)
                # Antivirus check
                try:
                    antivirus_file_validator(file_path)
                except ValidationError as e:
                    return JsonResponse(dict(error=str(e)), status=400)
                # Get url
                if path:
                    url = base_url + '/' + path + '/' + file_name
                else:
                    url = base_url + '/' + file_name
                urls.append(url)
            if action == 'upload_single':
                for url in urls:
                    msg += '\n' + url
                messages.success(request, msg)
                return HttpResponseRedirect('%s#/%s' % (red_url, path))
            else:
                return JsonResponse(dict(message=msg, urls=urls))

        # Folder form
        elif action == 'add_folder':
            # Check data
            path = request.POST.get('path', '').strip('/')
            if '..' in path:
                return JsonResponse(dict(error=_('Invalid base path.')), status=400)
            name = request.POST.get('name')
            if not name:
                return JsonResponse(dict(error=_('The "%s" field is required.') % 'name'), status=400)
            name = clean_file_name(name)
            if not name:
                return JsonResponse(dict(error=_('Invalid name.')), status=400)
            # Execute action
            if path:
                target = os.path.join(base_path, path, name)
            else:
                target = os.path.join(base_path, name)
            try:
                os.makedirs(target, exist_ok=True)
            except Exception as e:
                return JsonResponse(dict(error='%s %s' % (_('Failed to create folder:'), e)), status=400)
            return JsonResponse(dict(message=_('Folder created.')))

        # Actions on several files form
        elif action in ('rename', 'move', 'delete'):
            # Check data
            path = request.POST.get('path', '').strip('/')
            if '..' in path:
                return JsonResponse(dict(error=_('Invalid base path.')), status=400)
            if path:
                dir_path = os.path.join(base_path, path)
            else:
                dir_path = base_path
            names = list()
            for key in request.POST:
                if key.startswith('name_') and request.POST[key]:
                    names.append(request.POST[key])
            if not names:
                return JsonResponse(dict(error=_('No files selected.')), status=400)

            if action == 'rename':
                new_name = request.POST.get('new_name')
                if not new_name:
                    return JsonResponse(dict(error=_('The "%s" field is required.') % 'new_name'), status=400)
                new_name = clean_file_name(new_name)
                new_name_ext = ''
                if '.' in new_name and not (new_name.startswith('.') and new_name.count('.') == 1):
                    new_name_ext = '.' + new_name.split('.')[-1].lower()
                    new_name = new_name[:-len(new_name_ext)]
                if not new_name or new_name == '.htaccess':
                    return JsonResponse(dict(error=_('Invalid name.')), status=400)
                # Execute action
                index = 0
                for name in names:
                    src = os.path.join(dir_path, name)
                    if not os.path.exists(src):
                        return JsonResponse(dict(error=_('The file "%s" does not exist.') % src), status=400)
                    if len(names) == 1:
                        new = '%s%s' % (new_name, new_name_ext)
                    else:
                        index += 1
                        new = '%s-%s%s' % (new_name, index, new_name_ext)
                    dest = os.path.join(dir_path, new)
                    if src != dest:
                        if os.path.exists(dest):
                            return JsonResponse(dict(error=_('The file "%s" already exists.') % new), status=400)
                        os.rename(src, dest)
                if len(names) == 1:
                    return JsonResponse(dict(message=_('File renamed.')))
                else:
                    return JsonResponse(dict(message=_('Files renamed.')))

            elif action == 'move':
                new_path = request.POST.get('new_path', '').strip('/')
                if not new_path:
                    return JsonResponse(dict(error=_('No path specfied to move files in.')), status=400)
                if new_path == '#':
                    new_path = base_path
                else:
                    new_path = os.path.join(base_path, new_path)
                new_path = new_path
                if not os.path.exists(new_path):
                    return JsonResponse(dict(error=_('Destination path does not exists.')), status=400)
                moved = 0
                for name in names:
                    src = os.path.join(dir_path, name)
                    if src != new_path and not (os.path.isfile(src) and os.path.dirname(src) == new_path):
                        try:
                            shutil.move(src, new_path)
                            moved += 1
                        except Exception as e:
                            return JsonResponse(dict(error='%s %s' % (_('Unable to move file %s:') % name, e)), status=400)
                return JsonResponse(dict(message=_('%s file(s) successfully moved.') % moved))

            elif action == 'delete':
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
                    except Exception as e:
                        return JsonResponse(dict(error='%s %s' % (_('Unable to delete file %s:') % name, e)), status=400)
                return JsonResponse(dict(message=_('%(f)s file(s) and %(d)s directory(ies) successfully deleted.') % dict(f=files_deleted, d=dir_deleted)))
    else:
        # Actions using get method
        action = request.GET.get('action')
        # Search form
        if action == 'search':
            # Get path
            path = request.GET.get('path', '').strip('/')
            if '..' in path:
                return JsonResponse(dict(error=_('Invalid base path.')), status=400)
            if path:
                dir_path = os.path.join(base_path, path)
            else:
                dir_path = base_path
            if not os.path.exists(dir_path):
                return JsonResponse(dict(error=_('Requested path does not exist.')), status=400)
            # Get search command
            search = request.GET.get('search', '')
            search = search.replace('\'', '"').lower()

            dirs = dict()
            results = 0
            for bpath, subdirs, files in os.walk(dir_path):
                for name in subdirs:
                    if '/' in name:
                        name = name.split('/')[-1]
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
                    if '/' in name:
                        name = name.split('/')[-1]
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
            urls = list(dirs.keys())
            urls.sort()
            dirs = [dict(url=url, files=dirs[url]) for url in urls]

            if dirs:
                if path:
                    msg = _('%(count)s results for "%(search)s" in "%(path)s".') % dict(count=results, search=search, path=path)
                else:
                    msg = _('%(count)s results for "%(search)s".') % dict(count=results, search=search)
            else:
                msg = _('No results for "%(search)s".') % dict(search=search)

            return JsonResponse(dict(search_in=path, msg=msg, results=results, dirs=dirs))

    return JsonResponse(dict(error=_('Invalid action requested.')), status=400)
