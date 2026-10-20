import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture()
def staff_client(client):
    from django.contrib.auth.models import User
    user = User(username='fb_admin', is_staff=True)
    user.set_password('test')
    user.save()
    response = client.post(reverse('login'), {'username': user.username, 'password': 'test'})
    assert response.status_code == 302
    return client


def test_anonymous(client):
    response = client.get(reverse('storage:file_browser_base'))
    assert response.status_code == 302

    response = client.get(reverse('storage:file_browser_dirs'))
    assert response.status_code == 302

    response = client.get(reverse('storage:file_browser_content'), {'path': '/'})
    assert response.status_code == 302


def test_logged(staff_client):
    response = staff_client.get(reverse('storage:file_browser_base'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/html; charset=utf-8'

    response = staff_client.get(reverse('storage:file_browser_dirs'))
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    assert content == {
        'dirs': [
            {
                'dir_name': 'Root folder',
                'sub_dirs': [
                    {
                        'dir_name': 'a dir',
                        'sub_dirs': []
                    },
                    {
                        'dir_name': 'logs',
                        'sub_dirs': [],
                    },
                ]
            }
        ]
    }

    response = staff_client.get(reverse('storage:file_browser_content'), {'path': '/'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    content = json.loads(response.content.decode('utf-8'))
    content['files'][2]['mdate'] = 'test'
    assert content == {
        'files': [
            {
                'name': 'a dir',
                'size': 2069,
                'size_h': '2.1 kB',
                'is_dir': True,
                'nb_files': 2,
                'nb_dirs': 0
            },
            {
                'name': 'logs',
                'size': 873,
                'size_h': '873 B',
                'is_dir': True,
                'nb_files': 3,
                'nb_dirs': 0,
            },
            {
                'name': 'image.png',
                'size': 103,
                'size_h': '103 B',
                'is_dir': False,
                'nb_files': 0,
                'nb_dirs': 0,
                'ext': 'png',
                'preview': True,
                'mdate': 'test'
            }
        ],
        'path': '/',
        'total_size': '3.0 kB',
        'total_nb_dirs': 2,
        'total_nb_files': 6
    }

    response = staff_client.get(reverse('storage:file_browser_img_preview'), {'path': '/image.png'})
    assert response.status_code == 200
    assert response['Content-Type'] == 'image/png; charset=utf-8'
    assert len(response.content) > 0


@pytest.fixture()
def storage(settings, tmp_path):
    """
    Temporary storage with a sibling "outside" directory which must never be reachable.
    """
    base = tmp_path / 'storage'
    base.mkdir()
    (base / 'sub').mkdir()
    (base / 'sub' / 'file.txt').write_text('content')
    (base / 'a..b.txt').write_text('dots')
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.txt').write_text('secret')
    settings.FILE_BROWSER_DIRS = {'storage': (str(base), '/storage')}
    settings.ANTIVIRUS_ENABLED = False
    return base, outside


@pytest.mark.parametrize('path', ['../outside', 'sub/../../outside', '../../../../../../etc'])
def test_content__traversal(staff_client, storage, path):
    response = staff_client.get(reverse('storage:file_browser_content'), {'path': path})
    assert response.status_code == 400


def test_content__sub_dir(staff_client, storage):
    response = staff_client.get(reverse('storage:file_browser_content'), {'path': 'sub/'})
    assert response.status_code == 200
    content = json.loads(response.content.decode('utf-8'))
    assert [f['name'] for f in content['files']] == ['parent', 'file.txt']


def test_img_preview__traversal(staff_client, storage):
    base, outside = storage
    Image.new('RGB', (10, 10)).save(outside / 'image.png')
    response = staff_client.get(reverse('storage:file_browser_img_preview'), {'path': '../outside/image.png'})
    assert response.status_code == 302
    assert response['Location'].endswith('file_browser/img/img.png')


@pytest.mark.parametrize('name', ['../outside/secret.txt', '..', '.', 'sub/file.txt', '/tmp'])
@pytest.mark.parametrize('action', ['delete', 'rename', 'move'])
def test_action__invalid_names(staff_client, storage, action, name):
    base, outside = storage
    response = staff_client.post(reverse('storage:file_browser_action'), {
        'action': action, 'path': '', 'name_0': name, 'new_name': 'renamed', 'new_path': 'sub',
    })
    assert response.status_code == 400
    assert json.loads(response.content.decode('utf-8')) == {'error': 'Invalid name.'}
    assert (outside / 'secret.txt').exists()
    assert (base / 'sub' / 'file.txt').exists()


@pytest.mark.parametrize('data', [
    {'action': 'delete', 'path': '../outside', 'name_0': 'secret.txt'},
    {'action': 'rename', 'path': '../outside', 'name_0': 'secret.txt', 'new_name': 'renamed'},
    {'action': 'move', 'path': '../outside', 'name_0': 'secret.txt', 'new_path': 'sub'},
    {'action': 'move', 'path': 'sub', 'name_0': 'file.txt', 'new_path': '../outside'},
    {'action': 'add_folder', 'path': '../outside', 'name': 'new'},
])
def test_action__invalid_paths(staff_client, storage, data):
    base, outside = storage
    response = staff_client.post(reverse('storage:file_browser_action'), data)
    assert response.status_code == 400
    assert json.loads(response.content.decode('utf-8')) == {'error': 'Invalid base path.'}
    assert sorted(p.name for p in outside.iterdir()) == ['secret.txt']
    assert (base / 'sub' / 'file.txt').exists()


def test_action__upload_invalid_path(staff_client, storage):
    base, outside = storage
    response = staff_client.post(reverse('storage:file_browser_action'), {
        'action': 'upload', 'path': '../outside', 'file': SimpleUploadedFile('test.txt', b'test'),
    })
    assert response.status_code == 400
    assert not (outside / 'test.txt').exists()


def test_action__search_invalid_path(staff_client, storage):
    response = staff_client.get(reverse('storage:file_browser_action'), {
        'action': 'search', 'path': '../outside', 'search': 'secret',
    })
    assert response.status_code == 400


def test_action__search(staff_client, storage):
    response = staff_client.get(reverse('storage:file_browser_action'), {'action': 'search', 'search': 'file'})
    assert response.status_code == 200
    content = json.loads(response.content.decode('utf-8'))
    assert content['dirs'] == [{'url': 'sub/', 'files': ['file.txt']}]


def test_action__delete_symlink(staff_client, storage):
    base, outside = storage
    (base / 'link').symlink_to(outside, target_is_directory=True)
    response = staff_client.post(reverse('storage:file_browser_action'), {
        'action': 'delete', 'path': '', 'name_0': 'link',
    })
    assert response.status_code == 200
    assert not (base / 'link').exists()
    assert (outside / 'secret.txt').exists()


def test_action__valid_operations(staff_client, storage):
    base, outside = storage
    url = reverse('storage:file_browser_action')

    response = staff_client.post(url, {'action': 'add_folder', 'path': 'sub', 'name': 'new'})
    assert response.status_code == 200
    assert (base / 'sub' / 'new').is_dir()

    response = staff_client.post(url, {
        'action': 'upload', 'path': 'sub/new', 'file': SimpleUploadedFile('up.txt', b'test'),
    })
    assert response.status_code == 200
    assert (base / 'sub' / 'new' / 'up.txt').read_bytes() == b'test'

    response = staff_client.post(url, {'action': 'rename', 'path': '', 'name_0': 'a..b.txt', 'new_name': 'c.txt'})
    assert response.status_code == 200
    assert (base / 'c.txt').exists()

    response = staff_client.post(url, {'action': 'move', 'path': '', 'name_0': 'c.txt', 'new_path': 'sub/new'})
    assert response.status_code == 200
    assert (base / 'sub' / 'new' / 'c.txt').exists()

    response = staff_client.post(url, {'action': 'delete', 'path': 'sub', 'name_0': 'new'})
    assert response.status_code == 200
    assert not (base / 'sub' / 'new').exists()


def test_action__upload_invalid_name(staff_client, storage):
    response = staff_client.post(reverse('storage:file_browser_action'), {
        'action': 'upload', 'path': '', 'file': SimpleUploadedFile('!!!', b'test'),
    })
    assert response.status_code == 400


def test_messages__upload_links(staff_client, storage):
    response = staff_client.post(reverse('storage:file_browser_action'), {
        'action': 'upload_single', 'path': '<b>dir</b>', 'file': SimpleUploadedFile('up.txt', b'test'),
    }, follow=True)
    assert response.status_code == 200
    html = response.content.decode('utf-8')
    # The URL must be rendered as a link but the user values must be escaped
    url = '/storage/&lt;b&gt;dir&lt;/b&gt;/up.txt'
    assert f'<ul><li><a href="{url}">{url}</a></li></ul>' in html
    assert '<b>dir</b>' not in html


def test_messages__error_escaped(staff_client, storage):
    from django.contrib import messages
    from django.contrib.messages.storage.fallback import FallbackStorage
    from django.template.loader import render_to_string
    from django.test import RequestFactory
    request = RequestFactory().get('/')
    request.session = staff_client.session
    request._messages = FallbackStorage(request)
    messages.error(request, '<script>alert(1)</script>\nline 2')
    html = render_to_string('file_browser/body.html', request=request)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;<br>line 2' in html
