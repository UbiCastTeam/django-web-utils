#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Script to get a colored output for the flake8 command.
Author: Stéphane Diemer, stephane.diemer@ubicast.eu.

To use the last flake8 version on Ubuntu/Debian:
sudo apt purge pyflakes3 python3-flake8 python3-mccabe python3-pycodestyle python3-pyflakes flake8 python-pyflakes pep8 pycodestyle pyflakes
sudo apt install python3-pip
sudo pip3  install --upgrade pip
sudo pip3 install flake8

Flake8 codes:
https://pycodestyle.readthedocs.io/en/latest/intro.html#error-codes
http://flake8.pycqa.org/en/latest/user/error-codes.html

Ignored errors:
- E501: line too long
- E731: do not assign a lambda expression, use a def
- W503: line break before binary operator (deprecated rule)
- W505: doc line too long
'''
import os
import re
import subprocess
import sys


class PyflakesColor(object):
    __doc__
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'
    IGNORED = 'E501,E731,W503,W505'

    def __init__(self):
        object.__init__(self)
        self.returncode = 0

    def run(self, *args):
        if len(args) > 1:
            paths_to_check = args[1:]
        else:
            paths_to_check = '.'
        p = subprocess.run(['which', 'flake8'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if p.returncode != 0:
            print('Please install flake8 first', file=sys.stderr)
            sys.exit(1)
        error, warning, info = self.pyflakes_check(paths_to_check)
        print('Errors: %s, warnings: %s, information: %s' % (error, warning, info))
        return self.returncode

    def pyflakes_check(self, paths):
        error = warning = info = 0
        if not isinstance(paths, list) and not isinstance(paths, tuple):
            paths = [paths]
        for path in paths:
            if not os.path.exists(path):
                print('%sPath "%s" does not exists.%s' % (self.YELLOW, path, self.DEFAULT))
                continue
            # get flake8 command
            cmd = ['flake8']
            if self.IGNORED:
                cmd.append('--ignore=%s' % self.IGNORED)
            cmd.append(path)
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
            if p.returncode > self.returncode:
                self.returncode = p.returncode
            # parse flake8 result
            lines = p.stdout.strip().split('\n') if p.stdout else list()
            if not lines:
                if os.path.isfile(path):
                    print('%sFile: %s%s' % (self.PURPLE, path, self.DEFAULT))
                    print('    File is OK\n')
            else:
                lines.sort()
                last_path = None
                for line in lines:
                    if not line.strip():
                        continue
                    m = re.match(r'^(.*):(\d+):(\d+): (\w\d+) (.*)$', line)
                    if not m:
                        print(line)
                    else:
                        fpath, line_index, char_index, message_id, message_text = m.groups()
                        if not last_path or last_path != fpath:
                            last_path = fpath
                            print('%s%s:%s' % (self.PURPLE, fpath, self.DEFAULT))
                        if message_id in ('E265', 'E302', 'E402', 'F401', 'F403'):
                            color = self.BLUE
                            info += 1
                        elif message_id in ('E741', 'F841', 'W293') or message_id[:2] in ('E3', 'E4', 'E5'):
                            color = self.YELLOW
                            warning += 1
                        else:
                            color = self.RED
                            error += 1
                        print('    %s%s:%s: %s %s%s' % (color, line_index, char_index, message_id, message_text, self.DEFAULT))
        return error, warning, info


if __name__ == '__main__':
    pyflakes_color = PyflakesColor()
    sys.exit(pyflakes_color.run(*sys.argv))
