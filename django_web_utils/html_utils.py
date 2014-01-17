#!/usr/bin/env python
# -*- coding: utf-8 -*-
##----------------------------------------------------------------------------------
## HTML utility functions
##----------------------------------------------------------------------------------
import traceback
import re
import htmlentitydefs
# Django
from django.template import defaultfilters


# unescape function
#-----------------------------------------------------------------------------------
def unescape(text):
    text = defaultfilters.striptags(text)
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

# get_meta_tag_text function
#-----------------------------------------------------------------------------------
def get_meta_tag_text(text):
    result = defaultfilters.striptags(text)
    result = unescape(result)
    result = result.replace("\"", "''")
    return result

# get_html_traceback function
#-----------------------------------------------------------------------------------
def get_html_traceback():
    html = u'<p style="padding-left: 16px;">'
    error_tb = unicode(defaultfilters.escape(traceback.format_exc()))
    for line in error_tb.split(u'\n'):
        if line.startswith(u'    '):
            padding = u'32px'
        elif line.startswith(u'  '):
            padding = u'16px'
        else:
            padding = u'0'
        html += u'<span style="padding-left: %s;">%s</span><br/>' %(padding, line)
    html += u'</p>'
    return html

