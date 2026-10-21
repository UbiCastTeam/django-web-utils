"""
HTML utility functions
"""
from copy import deepcopy
from html import unescape as unescape_entities
import logging
import re
import traceback

from django.utils.html import escape
from django.utils.safestring import mark_safe
import nh3

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
# CSS properties always allowed in addition to ALLOWED_CSS
# (these properties were allowed by default by the "bleach" library previously used)
BASE_ALLOWED_CSS = {
    'azimuth', 'border-bottom-color', 'border-collapse', 'border-color', 'border-left-color',
    'border-right-color', 'border-top-color', 'clear', 'cursor', 'direction', 'display', 'elevation',
    'float', 'font', 'font-family', 'font-variant', 'letter-spacing', 'line-height', 'pause',
    'pause-after', 'pause-before', 'pitch', 'pitch-range', 'richness', 'speak', 'speak-header',
    'speak-numeral', 'speak-punctuation', 'speech-rate', 'stress', 'text-indent', 'unicode-bidi',
    'voice-family', 'volume', 'white-space',
    'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-linecap', 'stroke-linejoin',
    'stroke-opacity', 'stroke-width',
}
# Features allowed in the "allow" attribute of iframes (features like camera or microphone are refused)
ALLOWED_IFRAME_FEATURES = {
    'accelerometer', 'autoplay', 'clipboard-write', 'encrypted-media', 'fullscreen', 'gyroscope',
    'picture-in-picture', 'web-share',
}
URL_SCHEMES = {'http', 'https', 'mailto', 'data'}
A_HREF_PREFIXES = ('http:', 'https:', 'mailto:')
IMG_SRC_PREFIXES = A_HREF_PREFIXES + ('data:image/',)
LINE_RETURN_TAGS = {
    'div', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'tr',
    'fieldset', 'legend', 'pre', 'code', 'blockquote', 'video', 'source',
}
# Regex matching iframes (with their content) or any other tag in a HTML content cleaned by nh3.
# In the nh3 output, attribute values are always double quoted and "<" is always escaped in texts,
# so all tags can be matched reliably (quoted values are skipped in case "<" or ">" are not escaped in them).
CLEANED_IFRAME_RE = re.compile(r'(<iframe\b(?:[^>"]|"[^"]*")*>)(.*?)</iframe>|<(?:[^>"]|"[^"]*")*>', re.DOTALL)


def _filter_iframe_allow(value):
    """
    Keep only the allowed features in the "allow" attribute of an iframe.
    The value format is: "<feature> [<origins>]; <feature> [<origins>]; ...".
    """
    directives = [
        directive.strip()
        for directive in value.split(';')
        if directive.strip() and directive.split()[0].lower() in ALLOWED_IFRAME_FEATURES
    ]
    return '; '.join(directives) or None


def _attribute_filter(tag, name, value):
    """
    Check the value of URL attributes and of the "allow" attribute of iframes.
    The attribute is removed if None is returned.
    """
    if tag == 'iframe':
        if name == 'src':
            # Only HTTPS URLs and local paths are allowed (but not protocol relative URLs like "//host" or "/\\host")
            if value.startswith('https://') or (value.startswith('/') and not value.startswith(('//', '/\\'))):
                return value
            return None
        if name == 'allow':
            return _filter_iframe_allow(value)
    elif tag == 'img' and name == 'src':
        return value if value.lower().startswith(IMG_SRC_PREFIXES) else None
    elif tag == 'a' and name == 'href':
        return value if value.lower().startswith(A_HREF_PREFIXES) else None
    return value


def _clean_iframe_content(match, allow_iframes):
    """
    Remove all tags from the content of an iframe matched by CLEANED_IFRAME_RE.
    The content of iframes is not parsed as HTML by nh3 so tags like "script" are kept by it.
    The iframe tag is removed if iframes are not allowed.
    """
    start_tag, content = match.group(1, 2)
    if start_tag is None:
        # Not an iframe
        return match.group(0)
    content = strip_html_tags(content)
    return f'{start_tag}{content}</iframe>' if allow_iframes else content


def clean_html_tags(html, allow_iframes=False, extra_allowed_attrs=None, extra_allowed_css=None):
    """
    Function to remove all non allowed tags and attributes from the given HTML content.
    Non allowed tags are removed but their text content is kept (except for "script" and "style" tags).
    All tags are removed from the content of iframes.
    """
    if extra_allowed_css is None:
        extra_allowed_css = set()
    if extra_allowed_attrs is None:
        extra_allowed_attrs = {}
    allowed_attrs = deepcopy(ALLOWED_ATTRS)
    for key in extra_allowed_attrs.keys():
        if not allowed_attrs.get(key):
            allowed_attrs[key] = set(extra_allowed_attrs[key])
        else:
            allowed_attrs[key] |= set(extra_allowed_attrs[key])

    # Iframes are always kept by nh3 to be able to clean their content, they are removed afterwards if not allowed
    cleaned = nh3.clean(
        html,
        tags=ALLOWED_TAGS | {'iframe'},
        attributes=allowed_attrs,
        attribute_filter=_attribute_filter,
        filter_style_properties=BASE_ALLOWED_CSS | ALLOWED_CSS | extra_allowed_css,
        url_schemes=URL_SCHEMES,
        link_rel=None,
    )
    return CLEANED_IFRAME_RE.sub(lambda match: _clean_iframe_content(match, allow_iframes), cleaned)


def strip_html_tags(html):
    """
    Function to remove all HTML tags from the given content.
    The content of "script" and "style" tags is removed too.
    The remaining text is HTML escaped ("&" becomes "&amp;" for example).
    """
    return nh3.clean(html, tags=set())


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
    return mark_safe('\n<br/>'.join(lines))  # noqa: S308 (the traceback is escaped)
