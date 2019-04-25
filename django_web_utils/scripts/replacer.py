#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Stéphane Diemer stephane.diemer@ubicast.eu

import os
import sys
import re


class Replacer(object):
    '''This script replaces a given string with another one.'''

    DEFAULT_IGNORED = r'.*.(svn|git|bzr).*$|.*~$|.*.(svn|git|mo|po|pyc|jpg|bmp|png|gif|ttf|sql)$'
    PRINT_IGNORED = False

    USAGE = '''Usage:
    %s [-p=<path>] [-i=<ignore>] "old" "new" ["old2" "new2" ...]

Parameters:
    path:
        Path of file or dir in which all files will be processed.
        Default: current working dir: %s
    ignore:
        Regular expression matching file names to ignore.
        Default: %s
''' % (__file__, os.getcwd(), DEFAULT_IGNORED)

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'

    def run(self, *args):
        if not args or '-h' in args or '--help' in args:
            sys.stdout.write(self.__doc__ + '\n\n')
            sys.stdout.write(self.USAGE)
            return 0
        path = None
        ignore = None
        replacements = list()
        to_replace = None
        for arg in args:
            if arg.startswith('-p='):
                path = arg[3:]
            elif arg.startswith('-i='):
                ignore = arg[3:]
            elif not to_replace:
                if not arg:
                    continue
                to_replace = arg
            else:
                replacements.append((to_replace, arg))
                to_replace = None
        if to_replace:
            sys.stderr.write('Missing argument after a string to be replaced.\n')
            sys.stderr.write(self.USAGE)
            return 1

        return self.replace(replacements, path, ignore)

    def replace(self, replacements, path=None, ignore=None):
        if not path:
            path = os.getcwd()
        if not ignore:
            ignore = self.DEFAULT_IGNORED
        ignore_re = re.compile(ignore)
        sys.stdout.write('Replacement list is:\n    %s\n' % '\n    '.join(['"%s%s%s" -> "%s%s%s"' % (self.TEAL, r[0], self.DEFAULT, self.PURPLE, r[1], self.DEFAULT) for r in replacements]))
        sys.stdout.write('Starting script\n')
        analysed, changed, ignored = self._replace(path, replacements, ignore_re)
        sys.stdout.write('%s files analysed, %s files changed and %s files ignored.\n' % (analysed, changed, ignored))
        sys.stdout.write('Done\n')
        return 0

    def _replace(self, path, replacements, ignore_re):
        analysed = 0
        changed = 0
        ignored = 0
        if not os.path.exists(path):
            sys.stderr.write('%sThe path %s does not exist.%s\n' % (self.RED, path, self.DEFAULT))
            return analysed, changed, ignored
        if os.path.isdir(path):
            files = os.listdir(path)
            files.sort()
        else:
            files = [os.path.basename(path)]
            path = os.path.dirname(path)
        for picked_name in files:
            picked_path = os.path.join(path, picked_name)
            if os.path.isfile(picked_path):
                skipped = False
                if ignore_re.match(picked_path):
                    ignored += 1
                    skipped = True
                    if self.PRINT_IGNORED:
                        sys.stdout.write('    %sfile ignored:%s %s\n' % (self.GREEN, self.DEFAULT, picked_path))
                if not skipped:
                    # sys.stdout.write('    current file is: %s' % (picked_path)
                    analysed += 1
                    try:
                        with open(picked_path, 'r') as fd:
                            content = fd.read()
                    except UnicodeDecodeError:
                        # Binary file
                        continue

                    file_has_changed = False
                    for repl in replacements:
                        if repl[0] in content:
                            content = content.replace(repl[0], repl[1])
                            file_has_changed = True

                    if file_has_changed:
                        with open(picked_path, 'w+') as fd:
                            fd.write(content)
                        changed += 1
                        sys.stdout.write('    %sfile changed:%s %s\n' % (self.BLUE, self.DEFAULT, picked_path))

            elif os.path.isdir(picked_path):
                result = self._replace(picked_path, replacements, ignore_re)
                analysed += result[0]
                changed += result[1]
                ignored += result[2]
        return analysed, changed, ignored


if __name__ == '__main__':
    replacer = Replacer()
    sys.exit(replacer.run(*sys.argv[1:]))
