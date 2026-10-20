from PIL import Image
import pytest

from django_web_utils import images_utils


@pytest.fixture()
def image_path(tmp_path):
    path = tmp_path / 'image.png'
    Image.new('RGBA', (40, 20), (255, 0, 0, 255)).save(path)
    return path


def test_image_ratio(image_path, tmp_path):
    assert images_utils.get_image_ratio(image_path) == 2
    invalid = tmp_path / 'invalid.png'
    invalid.write_text('nope')
    assert images_utils.get_image_ratio(invalid) == 0


def test_image_info(image_path):
    info = images_utils.get_image_info(str(image_path))
    assert info['file_size'] == image_path.stat().st_size
    assert info['file_extension'] == 'png'
    assert info['image_width'] == 40
    assert info['image_height'] == 20


def test_rotate_image(image_path):
    dest = images_utils.rotate_image(str(image_path))
    assert dest.endswith('image_1.png')
    with Image.open(dest) as img:
        assert img.size == (20, 40)


def test_encode_as_jpeg(image_path):
    dest = images_utils.encode_as_jpeg(str(image_path))
    assert dest.endswith('image_1.jpg')
    with Image.open(dest) as img:
        assert img.format == 'JPEG'
        assert img.mode == 'RGB'
