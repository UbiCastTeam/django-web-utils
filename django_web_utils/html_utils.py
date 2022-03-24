#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
HTML utility functions
'''
from html.parser import HTMLParser
import bleach
import html.entities
import logging
import re
import traceback
from copy import deepcopy
# Django
from django.utils.html import escape
from django.utils.safestring import mark_safe

logger = logging.getLogger('djwutils.html_utils')

ALLOWED_TAGS = ['div', 'p', 'span', 'br', 'b', 'strong', 'i', 'em', 'u', 'sub', 'sup', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'img', 'fieldset', 'legend', 'pre', 'code', 'blockquote']
ALLOWED_ATTRS = {
    '*': ['class', 'style'],
    'a': ['href', 'target', 'title'],
    'img': ['alt', 'src', 'title'],
    'td': ['rowspan', 'colspan'],
    'th': ['rowspan', 'colspan'],
}
ALLOWED_STYLES = ['margin', 'padding', 'color', 'background', 'vertical-align', 'font-weight', 'font-size', 'font-style', 'text-decoration', 'text-align', 'text-shadow', 'border', 'border-radius', 'box-shadow', 'width', 'height']


# clean_html_tags function
# remove all non basic tags in the given html code
# ----------------------------------------------------------------------------
def clean_html_tags(html, allow_iframes=False):
    if allow_iframes:
        def iframe_attrs_check(tag, name, value):
            if name in ('name', 'height', 'width', 'allowfullscreen', 'class', 'style'):
                return True
            if name == 'src' and value.startswith('https://'):
                return True
            return False

        tags = list(ALLOWED_TAGS) + ['iframe']
        attrs = dict(ALLOWED_ATTRS)
        attrs['iframe'] = iframe_attrs_check
        return bleach.clean(html, tags=tags, attributes=attrs, styles=ALLOWED_STYLES)

    def img_attrs_check(tag, name, value):
        if name in ALLOWED_ATTRS['img']:
            if name == 'src':
                protocols = ['data:image/'] + bleach.sanitizer.ALLOWED_PROTOCOLS
                for protocol in protocols:
                    if value.startswith(protocol):
                        return True
                return False
            return True
        return False

    def a_attrs_check(tag, name, value):
        if name in ALLOWED_ATTRS['a']:
            if name == 'href':
                for protocol in bleach.sanitizer.ALLOWED_PROTOCOLS:
                    if value.startswith(protocol):
                        return True
                return False
            return True
        return False

    allowed_attrs = deepcopy(ALLOWED_ATTRS)
    allowed_attrs['img'] = img_attrs_check
    allowed_attrs['a'] = a_attrs_check
    protocols = bleach.sanitizer.ALLOWED_PROTOCOLS + ['data']
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=allowed_attrs, styles=ALLOWED_STYLES, protocols=protocols)


# strip_html_tags function
# remove all html tags
# ----------------------------------------------------------------------------
def strip_html_tags(html):
    return bleach.clean(html, strip=True)


# unescape function
# ----------------------------------------------------------------------------
def unescape(text):
    text = strip_html_tags(text)

    def fixup(m):
        text = m.group(0)
        if text[:2] == '&#':
            # character reference
            try:
                if text[:3] == '&#x':
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(html.entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub(r'&#?\w+;', fixup, text)


# get_meta_tag_text function
# ----------------------------------------------------------------------------
def get_meta_tag_text(text):
    result = unescape(text)
    result = strip_html_tags(result)
    result = result.strip().replace('"', '\'\'')
    return result


# get_html_traceback function
# ----------------------------------------------------------------------------
def get_html_traceback(tb=None):
    if not tb:
        tb = traceback.format_exc()
    error_tb = str(escape(tb))
    lines = list()
    for line in error_tb.split('\n'):
        if line:
            nb_spaces = len(line) - len(line.lstrip())
            lines.append(nb_spaces * '&nbsp;' + line[nb_spaces:])
        else:
            lines.append(line)
    return mark_safe('\n<br/>'.join(lines))


# get_short_text function
# ----------------------------------------------------------------------------
class TextHTMLParser(HTMLParser):
    def __init__(self, html_text, max_length=300):
        HTMLParser.__init__(self)
        self._short = ''
        self._length = 0
        self._stop = False
        self._tags_to_end = list()

        self._max_length = max_length
        self.feed(html_text)

    def handle_starttag(self, tag, attrs):
        if not self._stop:
            self._short += '<%s' % tag
            for attr in attrs:
                self._short += ' %s="%s"' % (attr[0], attr[1])
            self._short += '>'
            # add tag to list of tags to end
            self._tags_to_end.insert(0, tag)

    def handle_endtag(self, tag):
        if not self._stop:
            self._short += '</%s>' % tag
            # remove tag to list of tags to end
            if len(self._tags_to_end) != 0:
                if self._tags_to_end[0] == tag:
                    self._tags_to_end.pop(0)

    def handle_startendtag(self, tag, attrs):
        if not self._stop:
            self._short += '<%s' % tag
            for attr in attrs:
                self._short += ' %s="%s"' % (attr[0], attr[1])
            self._short += '/>'

    def handle_data(self, data):
        if not self._stop:
            if self._length + len(data) > self._max_length:
                self._stop = True
                data_length = self._max_length - self._length
                cut = data[:data_length]
                splitted = cut.split(' ')
                self._short += ' '.join(splitted[:(len(splitted) - 1)])
                self._short += ' ...'
                self._insert_tags_end()
            else:
                self._length += len(data)
                self._short += data

    def handle_charref(self, name):
        if not self._stop:
            self._short += '&#%s;' % name
            self._length += 1

    def handle_entityref(self, name):
        if not self._stop:
            self._short += '&%s;' % name
            self._length += 1

    def _insert_tags_end(self):
        for tag in self._tags_to_end:
            self._short += '</%s>' % tag

    def get_short(self):
        return self._short.strip()


def get_short_text(html_text, max_length=300, margin=100):
    '''
    Function to get an html text which does not exceed a given number of chars.
    ! Return empty if short text is not needed
    '''
    if len(html_text) > max_length + margin:
        try:
            parser = TextHTMLParser(html_text, max_length)
            return parser.get_short()
        except Exception as e:
            logger.error('Unable to create short html text. %s' % e)
    return ''
