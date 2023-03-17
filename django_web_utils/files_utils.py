"""
Files utility functions
"""
import os
import subprocess
from pathlib import Path
# Django
from django.utils.translation import gettext as _


def get_size(path, ignore_du_errors=True):
    """
    Function to get the size of a file or a dir.
    Dir size is retrieved using the "du" command (faster than Python).
    """
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        # "du" is much faster than getting size file of all files using python
        p = subprocess.run(['du', '-sb', str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = p.stdout.decode('utf-8').strip()
        err = p.stderr.decode('utf-8').strip()
        if not ignore_du_errors and p.returncode != 0:
            raise RuntimeError('Failed to get size using "du". Stdout: %s, Stderr: %s' % (out, err))
        try:
            return int(out.split('\t', 1)[0])
        except ValueError:
            raise RuntimeError('Failed to get size using "du". Stdout: %s, Stderr: %s' % (out, err))
    else:
        # Socket or something else
        return 0


def get_size_display(size=0, path=None):
    size, unit = get_unit(size, path)
    return f'{size} {unit}'


def get_unit(size=0, path=None):
    """
    DEPRECATED, use "get_size_display" instead of this function
    """
    if path is not None:
        size = get_size(path)
    if abs(size) <= 1000:
        unit = _('B')
    else:
        size /= 1000.0
        if abs(size) <= 1000:
            unit = _('kB')
        else:
            size /= 1000.0
            if abs(size) <= 1000:
                unit = _('MB')
            else:
                size /= 1000.0
                if abs(size) <= 1000:
                    unit = _('GB')
                else:
                    size /= 1000.0
                    unit = _('TB')
    size = round(size, 1)
    return size, unit


def get_new_path(path, new_extension=None):
    path = Path(path)
    fdir = path.parent
    fname = path.name.lower().strip('.')
    if '.' in fname:
        fname, fext = fname.rsplit('.', 1)
        if new_extension:
            fext = f'.{new_extension}'
        else:
            fext = f'.{fext}'
    else:
        fname = fname
        fext = f'.{new_extension}' if new_extension else ''
    count = 1
    if '_' in fname:
        name, count = fname.rsplit('_', 1)
        try:
            count = int(count)
        except ValueError:
            pass
        else:
            count += 1
            fname = name
    dest = fdir / f'{fname}_{count}{fext}'
    while dest.exists():
        count += 1
        dest = fdir / f'{fname}_{count}{fext}'
    return dest


def reverse_read(path, buf_size=8192):
    """
    Function to read a file starting from its end without loading it competely.
    UTF-8 decoding is not made in this function to avoid splitting unicode characters.
    """
    with open(path, 'rb') as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        total_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(total_size, offset + buf_size)
            fh.seek(-offset, os.SEEK_END)
            segment = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            yield segment
        yield None
