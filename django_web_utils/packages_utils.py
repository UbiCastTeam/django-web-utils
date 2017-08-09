#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Packages utility functions
'''
import datetime
import logging
import os
import subprocess

logger = logging.getLogger('djwutils.packages_utils')


def get_version(package=None, module=None):
    version = ''
    revision = ''
    if module:
        version = getattr(module, '__version__', '')
        git_dir = module.__path__[0]
        if os.path.islink(git_dir):
            git_dir = os.readlink(git_dir)
        if not os.path.exists(os.path.join(git_dir, '.git')):
            git_dir = os.path.dirname(git_dir)
            if not os.path.exists(os.path.join(git_dir, '.git')):
                git_dir = os.path.dirname(git_dir)
        git_dir = os.path.join(git_dir, '.git')
    else:
        git_dir = '.'
    cmds = [
        'dpkg -s \'%s\' | grep Version' % package,
        'git --git-dir \'%s\' log -1' % git_dir,
    ]
    local_repo = False
    for cmd in cmds:
        rc, out = subprocess.getstatusoutput(cmd)
        if rc == 0:
            if cmd.startswith('git'):
                local_repo = True
                # Get git repo version using last commit date and short hash
                try:
                    last_commit_unix_ts = subprocess.getoutput('git --git-dir \'%s\' log -1 --pretty=%%ct' % git_dir)
                    last_commit_ts = datetime.datetime.utcfromtimestamp(int(last_commit_unix_ts)).strftime('%Y%m%d%H%M%S')
                    last_commit_shorthash = subprocess.getoutput('git --git-dir \'%s\' log -1 --pretty=%%h' % git_dir)
                    revision = '%s-%s' % (last_commit_ts, last_commit_shorthash)
                except Exception as e:
                    logger.error('Unable to get revision: %s', e)
            else:
                revision = str(out, 'utf-8').replace('Version: ', '')
            break
    if '+' in revision:
        revision = revision[revision.index('+') + 1:]
    elif not revision:
        revision = '?'
    return version, revision, local_repo
