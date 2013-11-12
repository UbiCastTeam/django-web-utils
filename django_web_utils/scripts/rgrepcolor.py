#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import subprocess


class RGrepColor(object):
    IGNORED_EXTENSIONS = ['pyc', 'svn-base', 'mo', 'po']
    IGNORED_FILES = ['swfobject.js', 'jwplayer-5.9.js', 'jwplayer-5.10.js']
    IGNORED_PATHS = ['.svn', '/tiny_mce/']
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
    
    ALLOWED_OPTIONS = ('ignored_extensions', 'ignored_files', 'ignored_paths', 'ignore_big_lines', 'big_lines_length', 'case_sensitive')
    
    def __init__(self, options=None):
        object.__init__(self)
        for option in self.ALLOWED_OPTIONS:
            if options and option in options:
                setattr(self, option, options[option])
            else:
                default = getattr(self, option.upper())
                if isinstance(default, list):
                    default = list(default)
                if isinstance(default, dict):
                    default = dict(default)
                setattr(self, option, default)
    
    def run(self, *args):
        args = list(args)
        if '-i' in args:
            args.remove('-i')
            self.case_sensitive = False
        else:
            self.case_sensitive = True
        if len(args) < 2:
            raise Exception('Not enough arguments.')
        elif len(args) == 2:
            search = args[1]
            path = '.'
        elif len(args) == 3:
            search = args[1]
            path = args[2]
        else: # len(args) > 3:
            if args[len(args) - 1].startswith('-'):
                extensions = args[len(args) - 1].split('-')
                for ext in extensions:
                    if ext:
                        self.ignored_extensions.append(ext)
                path_index = len(args) - 2
            else:
                path_index = len(args) - 1
            search = args[1:path_index]
            search = ' '.join(search)
            path = args[path_index]
        self.rgrep(search, path)
    
    def rgrep(self, search, path):
        print 'Files with following extensions are ignored: %s%s%s' %(rgrep_color.PURPLE, ', '.join(self.ignored_extensions), rgrep_color.DEFAULT)
        print 'Following files are ignored: %s%s%s' %(rgrep_color.PURPLE, ', '.join(self.ignored_files), rgrep_color.DEFAULT)
        print 'Following paths are ignored: %s%s%s' %(rgrep_color.PURPLE, ', '.join(self.ignored_paths), rgrep_color.DEFAULT)
        print 'Searching for |%s%s%s|' %(rgrep_color.YELLOW, search, rgrep_color.DEFAULT)
        if self.case_sensitive:
            case = ''
        else:
            case = ' -i'
        search = search.replace('\'', '\'\\\'\'')
        search = search.replace('\\ ', ' ')
        p = subprocess.Popen('rgrep -F%s -n \'%s\' %s' %(case, search, path), stdout=subprocess.PIPE, stderr=sys.stderr, shell=True)
        result = p.communicate()[0]
        search = search.replace('\ ', ' ')
        search = search.replace('\'\\\'\'', '\'')
        lines = result.split('\n')
        last_file = None
        results = 0
        results_files = 0
        for line in lines:
            if line.startswith('grep: '):
                print '%sError: %s%s' %(self.RED, self.DEFAULT, line)
            else:
                splitted = line.split(':')
                if len(splitted) > 2:
                    current_file = splitted[0]
                    ign = False
                    for ign_path in self.ignored_paths:
                        if ign_path in current_file:
                            ign = True
                            break
                    if ign:
                        continue
                    file_name = current_file.split('/')[-1]
                    if file_name in self.ignored_files:
                        continue
                    tmp = current_file.split('.')
                    extension = tmp[len(tmp) - 1]
                    if extension not in self.ignored_extensions:
                        if last_file != current_file:
                            last_file = current_file
                            file_path = '.'.join(tmp[:len(tmp) - 1])
                            if current_file.endswith('~'):
                                file_path = file_path.replace(search, '%s%s%s' %(self.RED, search, self.BLUE))
                                print '%sFile %s.%s%s%s' %(self.BLUE, file_path, self.RED, extension, self.DEFAULT)
                            else:
                                file_path = file_path.replace(search, '%s%s%s' %(self.RED, search, self.BLUE))
                                print '%sFile %s.%s%s' %(self.BLUE, file_path, extension, self.DEFAULT)
                            results_files += 1
                        results += 1
                        code = ':'.join(splitted[2:])
                        code = code.replace(search, '%s%s%s' %(self.RED, search, self.DEFAULT))
                        if self.ignore_big_lines and len(code) > self.big_lines_length:
                            print '%s    Line %s: %s%s' %(self.GREEN, splitted[1], self.DEFAULT, 'ignored line (too long)')
                        else:
                            print '%s    Line %s: %s%s' %(self.GREEN, splitted[1], self.DEFAULT, code)
        if results:
            print '%s results in %s files' %(results, results_files)
        else:
            print 'No result found'


if __name__ == '__main__':
    rgrep_color = RGrepColor()
    rgrep_color.run(*sys.argv)

