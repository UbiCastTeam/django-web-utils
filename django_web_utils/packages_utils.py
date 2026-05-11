"""
Packages utility functions
"""
import datetime
import logging
from pathlib import Path
import subprocess

logger = logging.getLogger('djwutils.packages_utils')


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
    cmds = [
        f"dpkg -s '{package}' | grep Version",
        f"git --git-dir '{git_dir}' log -1",
    ]
    local_repo = False
    for cmd in cmds:
        rc, out = subprocess.getstatusoutput(cmd)
        if rc == 0:
            if cmd.startswith('git'):
                local_repo = True
                # Get git repo version using last commit date and short hash
                try:
                    commit_unix_ts = subprocess.getoutput(f"git --git-dir '{git_dir}' log -1 --pretty=%ct")
                    commit_date = datetime.datetime.fromtimestamp(
                        int(commit_unix_ts), datetime.UTC
                    ).strftime('%Y%m%d-%H%M%S')
                    commit_shorthash = subprocess.getoutput(f"git --git-dir '{git_dir}' log -1 --pretty=%h")
                    revision = f'{commit_date}-{commit_shorthash}'
                except Exception as e:
                    logger.warning('Unable to get revision: %s', e)
            else:
                revision = out.replace('Version: ', '')
            break
    if '+' in revision:
        revision = revision[revision.index('+') + 1:]
    elif not revision:
        revision = '?'
    return version, revision, local_repo
