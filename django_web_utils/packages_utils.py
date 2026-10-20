"""
Packages utility functions
"""
import datetime
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger('djwutils.packages_utils')


def _run(cmd):
    """
    Run a command without shell and return its return code and its output.
    """
    try:
        p = subprocess.run(
            cmd, encoding='utf-8',
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    except OSError as err:
        logger.debug('Failed to run command %s: %s', cmd, err)
        return 1, ''
    return p.returncode, p.stdout.strip()


def get_version(package=None, module=None):
    version = ''
    revision = ''
    if module:
        version = getattr(module, '__version__', '')
        git_dir = Path(module.__path__[0]).resolve() / '.git'
        for _i in range(3):
            if git_dir.exists():
                break
            git_dir = git_dir.parent.parent / '.git'
    else:
        git_dir = '.'
    local_repo = False
    rc, out = _run(['dpkg-query', '--show', '--showformat=${Version}', str(package)]) if package else (1, '')
    if rc == 0 and out:
        revision = out
    else:
        rc, out = _run(['git', '--git-dir', str(git_dir), 'log', '-1', '--pretty=%ct %h'])
        if rc == 0:
            local_repo = True
            # Get git repo version using last commit date and short hash
            try:
                commit_unix_ts, commit_shorthash = out.split(' ', 1)
                commit_date = datetime.datetime.fromtimestamp(
                    int(commit_unix_ts), datetime.UTC
                ).strftime('%Y%m%d-%H%M%S')
                revision = f'{commit_date}-{commit_shorthash}'
            except ValueError as e:
                logger.warning('Unable to get revision: %s', e)
    if '+' in revision:
        revision = revision[revision.index('+') + 1:]
    elif not revision:
        revision = '?'
    return version, revision, local_repo
