#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys


class Replacer(object):
    PATH = '/sources/mediaserver-work/mediaserver/mediaserver/'
    #PATH = '/sources/mediaserver-work/mediaserver-monitor/'
    #PATH = '/sources/celerity/'
    #PATH = '/sources/skyreach/trunk/skyreach_site/'
    #PATH = '/sources/easycast/trunk/'
    #PATH = '/sources/webinar_app/core/'
    #PATH = '/sources/ubicast-website-work/website/ubicast/'
    REPLACEMENT_LIST = [
        ('mimetype=', 'content_type='),
    ]
    
    IGNORED_FILES = ['~', '.svn', '.mo', '.po', '.pyc', '.jpg', '.bmp', '.png', '.gif', '.ttf', '.sql', '.js', '.css']
    PRINT_IGNORED = False
    
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'
    
    ALLOWED_OPTIONS = ('path', 'replacement_list', 'ignored_files', 'print_ignored')
    
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
        path = self.path
        replacement_list = self.replacement_list
        if len(args) > 1:
            path = args[1]
            if len(args) > 3:
                replacement_list = [(args[2], args[3])]
        
        self.replace(path, replacement_list)
    
    def replace(self, path, replacement_list):
        print u'Replacement list is:\n    %s' % u'\n    '.join([u'"%s%s%s" -> "%s%s%s"' %(self.TEAL, r[0], self.DEFAULT, self.PURPLE, r[1], self.DEFAULT) for r in replacement_list])
        print u'Starting script'
        analysed, changed, ignored = self._replace(path, replacement_list)
        print u'%s files analysed, %s files changed and %s files ignored' % (analysed, changed, ignored)
        print u'Done'
    
    def _replace(self, path, replacement_list):
        analysed = 0
        changed = 0
        ignored = 0
        if not os.path.exists(path):
            print u'%sThe path %s does not exist.%s' % (self.RED, path, self.DEFAULT)
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
                for ignored_file in self.ignored_files:
                    if ignored_file in picked_path:
                        ignored += 1
                        skipped = True
                        if self.print_ignored:
                            print u'%s    file ignored (contain %s):%s %s' % (self.GREEN, ignored_file, self.DEFAULT, picked_path)
                if not skipped:
                    analysed += 1
                    
                    #print '    current file is: %s' % (picked_path)
                    picked_file = open(picked_path, 'r')
                    content = picked_file.read()
                    picked_file.close()
                    
                    file_has_changed = False
                    for replacement in replacement_list:
                        if replacement[0] in content:
                            content = content.replace(replacement[0], replacement[1])
                            file_has_changed = True
                    
                    if file_has_changed:
                        picked_file = open(picked_path, 'w+')
                        picked_file.write(content)
                        #picked_file.write(content.encode('utf-8'))
                        picked_file.close()
                        
                        changed += 1
                        print u'%s    file changed:%s %s' % (self.BLUE, self.DEFAULT, picked_path)
            
            elif os.path.isdir(picked_path):
                result = self._replace(picked_path, replacement_list)
                analysed += result[0]
                changed += result[1]
                ignored += result[2]
        return analysed, changed, ignored


if __name__ == '__main__':
    replacer = Replacer()
    replacer.run(*sys.argv)

