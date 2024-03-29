from PIL import Image
import datetime
import logging
import os
# Django
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.templatetags.static import static
from django.utils.translation import gettext as _
# Django web utils
from django_web_utils.file_browser import config
from django_web_utils.files_utils import get_size_display

logger = logging.getLogger('djwutils.file_browser.views')

IMAGES_EXTENSION = ['png', 'gif', 'bmp', 'tiff', 'jpg', 'jpeg']


@config.view_decorator
def storage_manager(request, namespace=None):
    """
    Storage manager view.
    """
    base_url = config.get_base_url(namespace)
    tplt = config.BASE_TEMPLATE if config.BASE_TEMPLATE else 'file_browser/base.html'
    return render(request, tplt, {
        'base_url': base_url,
        'namespace': config.clean_namespace(namespace),
    })


def recursive_dirs(path):
    """
    Function to get all sub dirs from a dir recursively.
    """
    dirs = list()
    try:
        files_names = os.listdir(path)
    except OSError as e:
        logger.error(e)
    else:
        files_names.sort(key=lambda f: f.lower())
        for file_name in files_names:
            if '\'' in file_name or '"' in file_name:
                continue
            current_path = os.path.join(path, file_name)
            if os.path.isdir(current_path):
                dirs.append(dict(dir_name=file_name, sub_dirs=recursive_dirs(current_path)))
    return dirs


@config.view_decorator
def storage_dirs(request, namespace=None):
    """
    Storage dirs view.
    """
    base_path = config.get_base_path(namespace)

    if not os.path.exists(base_path):
        return JsonResponse(dict(error=_('Folder "%s" does not exist.') % base_path), status=400)

    dirs = [dict(dir_name=_('Root folder'), sub_dirs=recursive_dirs(base_path))]
    return JsonResponse(dict(dirs=dirs))


def get_info(path):
    """
    Function to get information on a path.
    """
    size = 0
    nb_files = 0
    nb_dirs = 0
    if os.path.isfile(path):
        size = os.path.getsize(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for name in files:
                try:
                    size += os.path.getsize(os.path.join(root, name))
                except OSError:
                    pass
            nb_files += len(files)
            nb_dirs += len(dirs)
    return size, nb_files, nb_dirs


@config.view_decorator
def storage_content(request, namespace=None):
    """
    Storage content view.
    """
    base_path = config.get_base_path(namespace)
    path = request.GET.get('path', '').strip('/')
    folder_path = base_path if not path else os.path.join(base_path, path)

    if not os.path.exists(folder_path):
        return JsonResponse(dict(error=_('Folder "%s" does not exist') % path), status=400)

    try:
        files_names = os.listdir(folder_path)
    except OSError as e:
        logger.error(e)
        return JsonResponse(dict(error=str(e)), status=400)
    if '.htaccess' in files_names:
        files_names.remove('.htaccess')

    # Content list
    total_size = 0
    total_nb_dirs = 0
    total_nb_files = 0
    files = list()
    folder_index = 0
    for file_name in files_names:
        current_path = os.path.join(folder_path, file_name)
        size, nb_files, nb_dirs = get_info(current_path)
        total_size += size
        total_nb_files += nb_files
        total_nb_dirs += nb_dirs
        file_properties = {
            'name': file_name,
            'size': size,
            'size_h': get_size_display(size),
            'is_dir': False,
            'nb_files': nb_files,
            'nb_dirs': nb_dirs,
        }
        if os.path.isdir(current_path):
            total_nb_dirs += 1
            file_properties['is_dir'] = True
            files.insert(folder_index, file_properties)
            folder_index += 1
        elif os.path.isfile(current_path):
            total_nb_files += 1
            splitted = file_name.split('.')
            file_properties['ext'] = splitted[-1].lower() if len(splitted) > 0 else ''
            if file_properties['ext'] in IMAGES_EXTENSION and size < 10000000:
                # Allow previes for images < 10MB
                file_properties['preview'] = True
            # Get modification time
            mdate = datetime.datetime.fromtimestamp(os.path.getmtime(current_path)).strftime('%Y-%m-%d %H:%M')
            file_properties['mdate'] = mdate
            files.append(file_properties)
        # Else: socket or other, ignored
    total_size = get_size_display(total_size)

    # Ordering
    order = request.GET.get('order', 'name-asc')
    if order.startswith('size'):
        if order.endswith('asc'):
            files.sort(key=lambda f: (not f['is_dir'], f['size']))
        else:
            files.sort(key=lambda f: (f['is_dir'], f['size']))
            files.reverse()
    elif order.startswith('mdate'):
        if order.endswith('asc'):
            files.sort(key=lambda f: (not f['is_dir'], f.get('mdate')))
        else:
            files.sort(key=lambda f: (f['is_dir'], f.get('mdate')))
            files.reverse()
    else:
        if order.endswith('asc'):
            files.sort(key=lambda f: (not f['is_dir'], f['name'].lower()))
        else:
            files.sort(key=lambda f: (f['is_dir'], f['name'].lower()))
            files.reverse()

    if path:
        files.insert(0, {
            'name': 'parent',
            'formated_name': '← %s' % _('Parent folder'),
            'is_dir': True,
            'isprevious': True,
        })

    return JsonResponse(dict(
        files=files,
        path='/' + path,
        total_size=total_size,
        total_nb_dirs=total_nb_dirs,
        total_nb_files=total_nb_files,
    ))


@config.view_decorator
def storage_img_preview(request, namespace=None):
    """
    Storage image preview view.
    """
    base_path = config.get_base_path(namespace)
    path = request.GET.get('path', '').strip('/')
    if not path:
        return HttpResponseRedirect(static('file_browser/img/img.png'))
    file_path = os.path.join(base_path, path)
    if not os.path.exists(file_path):
        return HttpResponseRedirect(static('file_browser/img/img.png'))

    try:
        image = Image.open(file_path)
        image.load()
        image.thumbnail((200, 64), Image.Resampling.LANCZOS)
    except Exception:
        return HttpResponseRedirect(static('file_browser/img/img.png'))

    if file_path.lower().endswith('jpg') or file_path.lower().endswith('jpeg'):
        response = HttpResponse(content_type='image/jpeg; charset=utf-8')
        image.save(response, 'JPEG', quality=85)
    else:
        response = HttpResponse(content_type='image/png; charset=utf-8')
        image.save(response, 'PNG')
    return response
