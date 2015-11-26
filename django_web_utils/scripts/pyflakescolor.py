#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Author: Stéphane Diemer stephane.diemer@ubicast.eu

from __future__ import print_function
import os
import sys
import subprocess


class PyflakesColor(object):
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'
    
    def __init__(self):
        object.__init__(self)
        self.returncode = 0
    
    def run(self, *args):
        if len(args) > 1:
            paths_to_check = args[1:]
        else:
            paths_to_check = '.'
        FNULL = open(os.devnull, 'w')
        pyflakes_present = subprocess.call(['which', 'pyflakes'], stdout=FNULL, stderr=FNULL) == 0
        if not pyflakes_present:
            print('Please install pyflakes')
            sys.exit(1)
        error, warning, info, other = self.pyflakes_check(paths_to_check)
        print('Errors: %s, warnings: %s, information: %s, others: %s' % (error, warning, info, other))
        return self.returncode
    
    def pyflakes_check(self, paths, display_result_for_all_files=False):
        error = warning = info = other = 0
        if not isinstance(paths, list) and not isinstance(paths, tuple):
            paths = [paths]
        for path in paths:
            if not os.path.exists(path):
                print('%sPath "%s" does not exists.%s' % (self.YELLOW, path, self.DEFAULT))
                continue
            if os.path.isfile(path):
                base_path = os.path.dirname(path)
                list_dir = [os.path.basename(path)]
                display_result_for_all_files = True
            elif os.path.isdir(path):
                base_path = path
                list_dir = os.listdir(path)
                list_dir.sort()
            else:
                print('%sPath "%s" is neither a file nor a directory.%s' % (self.YELLOW, path, self.DEFAULT))
                continue
            for picked_name in list_dir:
                picked_path = os.path.join(base_path, picked_name)
                if os.path.isfile(picked_path):
                    if picked_name.endswith('.py'):
                        text = 'file: %s \t path: %s' % (picked_name, picked_path)
                        p = subprocess.Popen(['python3', '-m', 'pyflakes', picked_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        out, err = p.communicate()
                        # decode from bytes to unicode
                        out = out.decode('utf-8') if out else ''
                        err = err.decode('utf-8') if err else ''
                        if p.returncode > self.returncode:
                            self.returncode = p.returncode
                        lines = out.split('\n') if out else list()
                        if err:
                            lines.extend(['        %s' % l if 'invalid syntax' not in l else l for l in err.split('\n')])
                        if len(lines) == 0 or (len(lines) == 1 and lines[0].strip() == ''):
                            if display_result_for_all_files:
                                print('%s%s%s' % (self.BLUE, text, self.DEFAULT))
                                print('    File is OK\n')
                        else:
                            print('%s%s%s' % (self.BLUE, text, self.DEFAULT))
                            for line in lines:
                                if not line.strip():
                                    continue
                                line = line.replace('%s:' % picked_path, 'line ')
                                if 'unable to detect undefined names' in line:
                                    color = self.GREEN
                                    info += 1
                                elif 'redefinition of function' in line or 'redefinition of unused' in line or 'is assigned to but never used' in line or 'imported but unused' in line:
                                    color = self.YELLOW
                                    warning += 1
                                elif 'undefined name' in line or 'referenced before assignment' in line or 'invalid syntax' in line:
                                    color = self.RED
                                    error += 1
                                else:
                                    color = self.DEFAULT
                                    other += 1
                                print('    %s%s%s' % (color, line, self.DEFAULT))
                elif os.path.isdir(picked_path):
                    e, w, i, o = self.pyflakes_check(picked_path, display_result_for_all_files)
                    error += e
                    warning += w
                    info += i
                    other += o
        return error, warning, info, other


if __name__ == '__main__':
    pyflakes_color = PyflakesColor()
    sys.exit(pyflakes_color.run(*sys.argv))
