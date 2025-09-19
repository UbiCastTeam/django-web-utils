"""
Zip utility functions
"""
import zipfile
from pathlib import Path


def _add_to_zip(zip_file, path, ignored=None, path_in_zip=None):
    for picked_path in Path(path).iterdir():
        if ignored and picked_path.name in ignored:
            continue
        picked_path_in_zip = path_in_zip + '/' + picked_path.name if path_in_zip else picked_path.name
        if picked_path.is_file():
            zip_file.write(picked_path, picked_path_in_zip)
        elif picked_path.is_dir():
            _add_to_zip(zip_file, picked_path, ignored, picked_path_in_zip)


def add_to_zip(path, zip_path, ignored=None, prefix=None, append=True):
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    mode = 'a' if append and zip_path.exists() else 'w'
    with zipfile.ZipFile(zip_path, mode) as zip_file:
        _add_to_zip(zip_file, path, ignored, path_in_zip=prefix)


def create_zip(path, zip_path, ignored=None, prefix=None):
    return add_to_zip(path, zip_path, ignored, prefix, append=False)


def get_zip_content_size(zip_path, extensions_filter=None):
    size = 0
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        zip_test = zip_file.testzip()
        if zip_test:
            raise zipfile.BadZipFile(f'CRC error on zip file: "{zip_test}"')

        for info in zip_file.infolist():
            if extensions_filter is None or Path(info.filename).suffix.lower() in extensions_filter:
                size += info.file_size
    return size


def unzip(path, zip_path, extensions_filter=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_file:
        zip_test = zip_file.testzip()
        if zip_test:
            raise zipfile.BadZipFile(f'CRC error on zip file: "{zip_test}"')

        members = None
        if extensions_filter:
            members = []
            for name in zip_file.namelist():
                ext = Path(name).suffix.lower()
                if ext in extensions_filter:
                    members.append(name)

        if members is None or members:
            zip_file.extractall(path=path, members=members)
