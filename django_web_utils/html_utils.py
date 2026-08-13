"""
HTML utility functions
"""
from copy import deepcopy
from html import unescape as unescape_entities
import logging
import re
import traceback

import bleach
from bleach.css_sanitizer import CSSSanitizer
from django.utils.html import escape
from django.utils.safestring import mark_safe

logger = logging.getLogger('djwutils.html_utils')

# For any change in the constants below, please update the same constant in the JSU project:
# https://github.com/UbiCastTeam/jsu/blob/main/vendors/tinymce/tinymce.custom.js
ALLOWED_TAGS = {
    'div', 'p', 'span', 'br', 'b', 'strong', 'i', 'em', 'u', 'sub', 'sup', 'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'img', 'fieldset', 'legend',
    'pre', 'code', 'blockquote', 'video', 'source',
}
ALLOWED_ATTRS = {
    '*': {
        'class', 'style', 'title', 'aria-label', 'aria-live',
        'role', 'aria-describedby', 'aria-description'
    },
    'a': {'href', 'target'},
    'img': {'alt', 'src'},
    'td': {'rowspan', 'colspan'},
    'th': {'rowspan', 'colspan'},
    'source': {'src', 'type'},
    'video': {'src', 'poster', 'loop', 'autoplay', 'muted', 'controls', 'playsinline', 'preload'},
    'iframe': {'src', 'width', 'height', 'scrolling', 'allow', 'allowfullscreen', 'frameborder', 'referrerpolicy'},
}
ALLOWED_CSS = {
    'margin-bottom', 'margin-left', 'margin-right', 'margin-top', 'margin',
    'padding-bottom', 'padding-left', 'padding-right', 'padding-top', 'padding',
    'color', 'background-image', 'background-color', 'background',
    'font-weight', 'font-size', 'font-style',
    'text-decoration', 'text-align', 'text-shadow',
    'border-bottom', 'border-left', 'border-right', 'border-top', 'border',
    'border-radius-bottom-left', 'border-radius-bottom-right', 'border-radius-top-left',
    'border-radius-top-right', 'border-radius',
    'box-shadow', 'width', 'height', 'overflow', 'vertical-align',
}
LINE_RETURN_TAGS = {
    'div', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'tr',
    'fieldset', 'legend', 'pre', 'code', 'blockquote', 'video', 'source',
}


def clean_html_tags(html, allow_iframes=False, extra_allowed_attrs=None, extra_allowed_css=None):
    """
    Function to remove all non allowed tags and attributes from the given HTML content.
    """
    if extra_allowed_css is None:
        extra_allowed_css = set()
    if extra_allowed_attrs is None:
        extra_allowed_attrs = {}
    allowed_attrs = deepcopy(ALLOWED_ATTRS)
    for key in allowed_attrs.keys():
        if key != '*':
            allowed_attrs[key] |= allowed_attrs['*']

    for key in extra_allowed_attrs.keys():
        if not allowed_attrs.get(key):
            allowed_attrs[key] = extra_allowed_attrs[key]
        else:
            allowed_attrs[key] |= extra_allowed_attrs[key]

    def iframe_attrs_check(_tag, name, value):
        if name == 'src':
            return value.startswith(('https://', '/'))
        if name in allowed_attrs['iframe']:
            return True
        return False

    def img_attrs_check(_tag, name, value):
        if name == 'src':
            protocols = bleach.sanitizer.ALLOWED_PROTOCOLS | {'data:image/'}
            for protocol in protocols:
                if value.startswith(protocol):
                    return True
            return False
        if name in allowed_attrs['img']:
            return True
        return False

    def a_attrs_check(_tag, name, value):
        if name == 'href':
            for protocol in bleach.sanitizer.ALLOWED_PROTOCOLS:
                if value.startswith(protocol):
                    return True
            return False
        if name in allowed_attrs['a']:
            return True
        return False

    callable_allowed_attrs = deepcopy(allowed_attrs)
    tags = set(ALLOWED_TAGS)
    if allow_iframes:
        callable_allowed_attrs['iframe'] = iframe_attrs_check
        tags |= {'iframe'}
    callable_allowed_attrs['img'] = img_attrs_check
    callable_allowed_attrs['a'] = a_attrs_check
    allowed_css = (
        bleach.css_sanitizer.ALLOWED_CSS_PROPERTIES
        | bleach.css_sanitizer.ALLOWED_SVG_PROPERTIES
        | ALLOWED_CSS
        | extra_allowed_css
    )
    css_sanitizer = CSSSanitizer(allowed_css_properties=allowed_css)
    protocols = bleach.sanitizer.ALLOWED_PROTOCOLS | {'data'}
    return bleach.clean(
        html,
        tags=tags,
        attributes=callable_allowed_attrs,
        css_sanitizer=css_sanitizer,
        protocols=protocols
    )


def strip_html_tags(html):
    """
    Function to remove all HTML tags from the given content.
    The remaining text is HTML escaped ("&" becomes "&amp;" for example).
    """
    return bleach.clean(html, tags=set(), strip=True)


def unescape(html):
    """
    Function to convert HTML content to unicode text content.
    """
    # Line returns in the source have no meaning in HTML
    text = html.replace('\r', ' ').replace('\n', ' ')
    # Add a space before every tag to avoid sticking words together
    text = text.replace('<', ' <')
    # Add a line return before block tags to keep the text structure
    text = re.sub(
        rf'</?({"|".join(LINE_RETURN_TAGS)})(\s[^>]*)?/?>',
        r'\n\g<0>', text, flags=re.IGNORECASE
    )
    # Remove all HTML tags
    text = strip_html_tags(text)
    # Normalize spaces but keep line returns
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\s*\n\s*', '\n', text).strip()
    # Replace entities and character references with their unicode equivalent
    return unescape_entities(text)


def get_meta_tag_text(html):
    """
    Function to get a text that can be safely used in an HTML "meta" tag.
    The returned content is expected to be used inside an HTML attributes using double quotes.
    """
    return unescape(html).replace('"', "''")


def get_short_text(html, max_length=300):
    """
    Function to get the text of an HTML content.
    The text is truncated if it is longer than "max_length" chars, the ellipsis being
    included in that limit.
    The returned text is not HTML escaped, it must be escaped when displayed.
    """
    # Remove all HTML tags and convert HTML entities
    result = unescape(html)
    # Cut content if too long
    if len(result) > max_length:
        # Keep some room for the ellipsis
        cut = max(max_length - 3, 0)
        truncated = result[:cut]
        if not result[cut:cut + 1].isspace():
            # The cut is in the middle of a word, remove it unless it is the only one
            match = re.search(r'\s\S*$', truncated)
            if match:
                truncated = truncated[:match.start()]
        result = truncated.rstrip() + '...'
    return result


def get_html_traceback(tb=None):
    """
    Function to get a Python traceback as HTML content.
    """
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
