"""
Files utility functions
"""
import datetime
import os
import subprocess
from pathlib import Path
from typing import Iterator, Optional

try:
    from django.utils.translation import gettext as _
except ImportError:
    def _(text):
        return text


def get_size(path: str | Path, ignore_du_errors: bool = True) -> int:
    """
    Function to get the size of a file or a dir.
    Dir size is retrieved using the "du" command (faster than Python).
    """
    path = Path(path)
    if path.is_file():
        return path.stat().st_size
    elif path.is_dir():
        # "du" is much faster than getting size file of all files using python
        p = subprocess.run(
            ['du', '-sb', str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
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


def get_size_repr(size: int) -> str:
    """
    Return human-readable size with automatic suffix.
    """
    unit = 'Y'
    for val in ('', 'k', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(size) < 1000:
            unit = val
            break
        size /= 1000
    return f'{round(size, 1)} {unit}B'


def get_size_display(size: int = 0, path: str | Path | None = None) -> str:
    """
    Return human-readable size with automatic suffix (translated unit).
    """
    if path is not None:
        size = get_size(path)
    return get_size_repr(size)[:-1] + _('B')


def get_new_path(path: str | Path, new_extension: str | None = None) -> Path:
    """
    Return a new name for an existing file.
    """
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


def reverse_read(path: str | Path, buf_size: int = 8192) -> Iterator:
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


def backup_file(file_path: Path, max_backups: int = 10) -> Optional[Path]:
    """
    Make a backup copy of a file.
    Only one backup is made per day and only the last 10 (default) backups are retained.
    This function is not intended to be used with large files as it reads entirely the source file to copy it.
    """
    if not file_path or not file_path.is_file():
        return

    mtime = file_path.stat().st_mtime
    date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')

    backup_path = file_path.parent / f'{file_path.name}.backup_{date_str}{file_path.suffix}'
    if backup_path.exists():
        return backup_path

    paths = sorted(
        path
        for path in file_path.parent.iterdir()
        if path.is_file() and path.name.startswith(f'{file_path.name}.backup_')
    )
    for i in range(0, len(paths) - max_backups + 1):
        paths[i].unlink(missing_ok=True)

    current = file_path.read_bytes()
    backup_path.write_bytes(current)
    backup_path.chmod(file_path.stat().st_mode)
    return backup_path
