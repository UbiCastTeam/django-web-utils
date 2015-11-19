#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Stéphane Diemer stephane.diemer@ubicast.eu

import sys
import subprocess


class RGrepColor(object):
    IGNORED_EXTENSIONS = ['pyc', 'svn-base', 'mo', 'po']
    IGNORED_FILES = []
    IGNORED_PATHS = ['.svn', '.git', '.bzr']
    IGNORE_BIG_LINES = True
    BIG_LINES_LENGTH = 500
    CASE_SENSITIVE = True
    
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'
    
    def __init__(self):
        object.__init__(self)
    
    def run(self, *args):
        args = list(args)
        if '-i' in args:
            args.remove('-i')
            self.CASE_SENSITIVE = False
        else:
            self.CASE_SENSITIVE = True
        if len(args) < 2:
            print('Usage: rgrepcolor.py myword')
            return 1
        elif len(args) == 2:
            search = args[1]
            path = '.'
        elif len(args) == 3:
            search = args[1]
            path = args[2]
        else:  # len(args) > 3:
            if args[len(args) - 1].startswith('-'):
                extensions = args[len(args) - 1].split('-')
                for ext in extensions:
                    if ext:
                        self.IGNORED_EXTENSIONS.append(ext)
                path_index = len(args) - 2
            else:
                path_index = len(args) - 1
            search = args[1:path_index]
            search = ' '.join(search)
            path = args[path_index]
        return self.rgrep(search, path)
    
    def rgrep(self, search, path):
        print('Files with following extensions are ignored: %s%s%s' % (rgrep_color.PURPLE, ', '.join(self.IGNORED_EXTENSIONS), rgrep_color.DEFAULT))
        print('Following files are ignored: %s%s%s' % (rgrep_color.PURPLE, ', '.join(self.IGNORED_FILES), rgrep_color.DEFAULT))
        print('Following paths are ignored: %s%s%s' % (rgrep_color.PURPLE, ', '.join(self.IGNORED_PATHS), rgrep_color.DEFAULT))
        print('Searching for |%s%s%s|' % (rgrep_color.YELLOW, search, rgrep_color.DEFAULT))

        command = ['rgrep', '-F', '-n']
        if not self.CASE_SENSITIVE:
            command.append('-i')
        command.append(search)
        command.append(path)
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=sys.stderr, shell=False)
        result = p.communicate()[0]

        lines = result.split(b'\n')
        last_file = None
        results = 0
        results_files = 0
        for line in lines:
            if line.startswith(b'grep: '):
                print('%sError: %s%s' % (self.RED, self.DEFAULT, line))
                return 1
            else:
                splitted = line.split(b':')
                if len(splitted) > 2:
                    current_file = str(splitted[0], 'utf-8')
                    ign = False
                    for ign_path in self.IGNORED_PATHS:
                        if ign_path in current_file:
                            ign = True
                            break
                    if ign:
                        continue
                    file_name = current_file.split('/')[-1]
                    if file_name in self.IGNORED_FILES:
                        continue
                    tmp = current_file.split('.')
                    extension = tmp[len(tmp) - 1]
                    if extension not in self.IGNORED_EXTENSIONS:
                        if last_file != current_file:
                            last_file = current_file
                            file_path = '.'.join(tmp[:len(tmp) - 1])
                            if current_file.endswith('~'):
                                file_path = file_path.replace(search, '%s%s%s' % (self.RED, search, self.BLUE))
                                print('%sFile %s.%s%s%s' % (self.BLUE, file_path, self.RED, extension, self.DEFAULT))
                            else:
                                file_path = file_path.replace(search, '%s%s%s' % (self.RED, search, self.BLUE))
                                print('%sFile %s.%s%s' % (self.BLUE, file_path, extension, self.DEFAULT))
                            results_files += 1
                        results += 1
                        code = str(b':'.join(splitted[2:]), 'utf-8')
                        code = code.replace(search, '%s%s%s' % (self.RED, search, self.DEFAULT))
                        if self.IGNORE_BIG_LINES and len(code) > self.BIG_LINES_LENGTH:
                            print('%s    Line %s: %s%s' % (self.GREEN, splitted[1], self.DEFAULT, 'ignored line (too long)'))
                        else:
                            print('%s    Line %s: %s%s' % (self.GREEN, splitted[1], self.DEFAULT, code))
        if results:
            print('%s results in %s files' % (results, results_files))
        else:
            print('No result found')
        return 0


if __name__ == '__main__':
    rgrep_color = RGrepColor()
    sys.exit(rgrep_color.run(*sys.argv))
