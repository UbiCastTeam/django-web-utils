# flake8: noqa: E501
import pytest

from django_web_utils import html_utils


@pytest.mark.parametrize('value,allow_iframes,expected', [
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe>', False,
        '&lt;iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"&gt;&lt;/iframe&gt;', id='escape_iframe'),
    pytest.param(
        '<iframe width="560" height="315" src="https://www.youtube.com/embed/l8PMl7tUDIE?si=B-IQYsfP8otwVPXg" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen="" referrerpolicy="strict-origin-when-cross-origin"></iframe>', True,
        '<iframe width="560" height="315" src="https://www.youtube.com/embed/l8PMl7tUDIE?si=B-IQYsfP8otwVPXg" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen="" referrerpolicy="strict-origin-when-cross-origin"></iframe>', id='allow_full_youtube_iframe'),
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe>', True,
        '<iframe allow="autoplay"></iframe>', id='escape_iframe_src'),
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', True,
        '<iframe allow="autoplay"></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', id='escape_multiple'),
    pytest.param(
        '<iframe src="https://localhost/test" allow="autoplay" nope="test"></iframe>', True,
        '<iframe src="https://localhost/test" allow="autoplay"></iframe>', id='iframe_https_src_allowed'),
    pytest.param(
        '<iframe src="http://localhost/test" allow="autoplay" nope="test"></iframe>', True,
        '<iframe allow="autoplay"></iframe>', id='iframe_http_src_denied'),
    pytest.param(
        '<iframe src="/test" allow="autoplay" nope="test"></iframe>', True,
        '<iframe src="/test" allow="autoplay"></iframe>', id='iframe_site_src_denied'),
    pytest.param(
        '<img src="data:image/png;base64,ABCD" style="width: 50%">', False,
        '<img src="data:image/png;base64,ABCD" style="width: 50%;">', id='conserve_base64_image'),
    pytest.param(
        '<a href="data:image/png;base64,ABCD">', False,
        '<a></a>', id='clean_a_base64_href'),
    pytest.param(
        '<a href="http://google.com" style="font-size: 75%"></a>', False,
        '<a href="http://google.com" style="font-size: 75%;"></a>', id='conserve_a_http_href'),
    pytest.param(
        '<iframe src="data:text/html,%3C%73%63%72%69%70%74%3E%61%6C%65%72%74%28%31%29%3C%2F%73%63%72%69%70%74%3E"></iframe>', True,
        '<iframe></iframe>', id='alert_in_src'),
    pytest.param(
        '<iframe data-custom="1" src="data:image/svg-xml,%1F%8B%08%00%00%00%00%00%02%03%B3)N.%CA%2C(Q%A8%C8%CD%C9%2B%B6U%CA())%B0%D2%D7%2F%2F%2F%D7%2B7%D6%CB%2FJ%D77%B4%B4%B4%D4%AF%C8(%C9%CDQ%B2K%CCI-*%D10%D4%B4%D1%87%E8%B2%03"></iframe>', True,
        '<iframe data-custom="1"></iframe>', id='download_in_src'),
    pytest.param(
        '''<div
            class="a" style="color: blue" title="b" aria-label="c"
            aria-live="polite" role="button" aria-describedby="id"
            aria-description="d"
        ></div>''', False,
        '<div class="a" style="color: blue;" title="b" aria-label="c" aria-live="polite" role="button" aria-describedby="id" aria-description="d"></div>', id='allowed_check'
    )
])
def test_clean_html_tags(value, allow_iframes, expected):
    assert html_utils.clean_html_tags(
        value,
        allow_iframes=allow_iframes,
        extra_allowed_attrs={'iframe': {'data-custom'}},
    ) == expected
    assert sorted(html_utils.ALLOWED_TAGS) == [
        'a',
        'b',
        'blockquote',
        'br',
        'code',
        'div',
        'em',
        'fieldset',
        'h1',
        'h2',
        'h3',
        'h4',
        'i',
        'img',
        'legend',
        'li',
        'ol',
        'p',
        'pre',
        'source',
        'span',
        'strong',
        'sub',
        'sup',
        'table',
        'tbody',
        'td',
        'th',
        'thead',
        'tr',
        'u',
        'ul',
        'video',
    ]


@pytest.mark.parametrize('value,extra_allowed_attrs,expected', [
    pytest.param(
        '<div data-name="the name">Sample</div>', {'div': {'data-custom'}},
        '<div>Sample</div>', id='default_allowed_attrs'),
    pytest.param(
        '<div data-name="the name">Sample</div>', {'div': {'data-name'}},
        '<div data-name="the name">Sample</div>', id='allow_data_name_attr'),
    pytest.param(
        '<iframe data-name="the name">Sample</iframe>', {'iframe': {'data-name'}},
        '&lt;iframe data-name="the name"&gt;Sample&lt;/iframe&gt;', id='iframe_not_allowed'),
])
def test_clean_html_tags__extra_attrs(value, extra_allowed_attrs, expected):
    assert html_utils.clean_html_tags(value, extra_allowed_attrs=extra_allowed_attrs) == expected
    assert sorted(html_utils.ALLOWED_ATTRS.keys()) == ['*', 'a', 'iframe', 'img', 'source', 'td', 'th', 'video']


@pytest.mark.parametrize('value,extra_allowed_css,expected', [
    pytest.param(
        '''
            <div style="width: 100%;">
                <div style="position: relative; padding-bottom: 56.25%; padding-top: 0; height: 0;">
                    <iframe title="Test" frameborder="0" width="1200px" height="675px"
                            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="https://test.test"
                            type="text/html" allowscriptaccess="always" allowfullscreen="true" scrolling="yes" allownetworking="all">
                    </iframe>
                </div>
            </div>
        ''', set(),
        '''
            <div style="width: 100%;">
                <div style="padding-bottom: 56.25%; padding-top: 0; height: 0;">
                    <iframe title="Test" frameborder="0" width="1200px" height="675px" style="width: 100%; height: 100%;" src="https://test.test" allowfullscreen="true" scrolling="yes">
                    </iframe>
                </div>
            </div>
        ''', id='default_allowed_css'
    ),
    pytest.param(
        '''
            <div style="width: 100%;">
                <div style="position: relative; padding-bottom: 56.25%; padding-top: 0; height: 0;">
                    <iframe title="Test" frameborder="0" width="1200px" height="675px"
                            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="https://test.test"
                            type="text/html" allowscriptaccess="always" allowfullscreen="true" scrolling="yes" allownetworking="all">
                    </iframe>
                </div>
            </div>
        ''', {'position', 'top', 'left', 'right', 'bottom'},
        '''
            <div style="width: 100%;">
                <div style="position: relative; padding-bottom: 56.25%; padding-top: 0; height: 0;">
                    <iframe title="Test" frameborder="0" width="1200px" height="675px" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="https://test.test" allowfullscreen="true" scrolling="yes">
                    </iframe>
                </div>
            </div>
        ''', id='extra_allowed_css'
    )
])
def test_clean_html__extra_css(value, extra_allowed_css, expected):
    assert html_utils.clean_html_tags(value, allow_iframes=True, extra_allowed_css=extra_allowed_css) == expected


@pytest.mark.parametrize('value,expected', [
    pytest.param('<p>para</p>', 'para', id='block_tag'),
    pytest.param('<b>bold</b>text', 'boldtext', id='bleach_default_allowed_tag'),
    pytest.param('<em>a</em><strong>b</strong>', 'ab', id='bleach_default_allowed_tags'),
    pytest.param('<a href="http://test.com">link</a>', 'link', id='link'),
    pytest.param('<script>alert(1)</script>', 'alert(1)', id='script_content_kept_as_text'),
    pytest.param('a & b', 'a &amp; b', id='escape_ampersand'),
    pytest.param('5 < 6', '5 &lt; 6', id='escape_lower_than'),
])
def test_strip_html_tags(value, expected):
    assert html_utils.strip_html_tags(value) == expected


@pytest.mark.parametrize('value,expected', [
    # No text to return
    pytest.param(
        '', '', id='empty'),
    pytest.param(
        '  \n  ', '', id='only_spaces'),
    pytest.param(
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/></p>',
        '', id='no_text'),
    # Tags removal
    pytest.param(
        '<p>Some <b>bold</b> and <em>italic</em> text</p>',
        'Some bold and italic text', id='inline_tags_removed'),
    pytest.param(
        '<a href="http://test.com">link</a> here',
        'link here', id='link_removed'),
    pytest.param(
        '<span>a</span><span>b</span>',
        'a b', id='words_not_stuck_together'),
    # Line returns
    pytest.param(
        '<p>First</p><p>Second</p>',
        'First\nSecond', id='line_return_between_blocks'),
    pytest.param(
        '<div class="a" title="b">x</div><div>y</div>',
        'x\ny', id='line_return_on_block_with_attrs'),
    pytest.param(
        'a<br/>b',
        'a\nb', id='line_return_on_br'),
    pytest.param(
        '<ul><li>a</li><li>b</li></ul>',
        'a\nb', id='line_return_on_list'),
    pytest.param(
        '<h1>Title</h1><p>Body</p>',
        'Title\nBody', id='line_return_on_heading'),
    pytest.param(
        '<span>a</span>\n<span>b</span>',
        'a b', id='source_line_returns_ignored'),
    pytest.param(
        '<p>\n  Multi\r\n  lines\n</p>',
        'Multi lines', id='source_line_returns_in_text'),
    # HTML entities
    pytest.param(
        '<b>Tom &amp; Jerry</b>', 'Tom & Jerry', id='named_entity'),
    pytest.param(
        '&eacute;t&eacute;', 'été', id='accented_named_entity'),
    pytest.param(
        '&lt;b&gt;not bold&lt;/b&gt;', '<b>not bold</b>', id='escaped_tags_are_text'),
    pytest.param(
        '&unknown;', '&unknown;', id='unknown_entity_left_as_is'),
    # HTML5 entities, unknown from the HTML4 table
    pytest.param(
        '&apos;', "'", id='html5_named_entity'),
    pytest.param(
        '&AMP;', '&', id='uppercase_named_entity'),
    # Character references
    pytest.param(
        '&#233;', 'é', id='decimal_reference'),
    pytest.param(
        '&#xe9;', 'é', id='hexadecimal_reference'),
    pytest.param(
        '&#XE9;', 'é', id='uppercase_hexadecimal_reference'),
    pytest.param(
        '&#x1F600;', '😀', id='astral_reference'),
    # The 0x80-0x9F range is remapped to windows-1252 as required by the HTML5 specification
    pytest.param(
        '&#151;', '—', id='windows_1252_reference'),
    # Invalid references are replaced to avoid null chars and lone surrogates
    pytest.param(
        '&#0;', '�', id='null_reference'),
    pytest.param(
        '&#xD800;', '�', id='surrogate_reference'),
    pytest.param(
        '&#99999999;', '�', id='out_of_range_reference'),
])
def test_unescape(value, expected):
    assert html_utils.unescape(value) == expected


@pytest.mark.parametrize('value,expected', [
    pytest.param('<b>bold</b> text', 'bold text', id='inline_tags_removed'),
    pytest.param('  <p>spaces</p>  ', 'spaces', id='stripped'),
    pytest.param('<p>He said "hello" &amp; left &lt;br&gt;</p>', "He said ''hello'' & left <br>", id='quotes_and_entities'),
])
def test_get_meta_tag_text(value, expected):
    assert html_utils.get_meta_tag_text(value) == expected


# The text extraction itself is covered by "test_unescape"
@pytest.mark.parametrize('value,max_length,expected', [
    pytest.param(
        '', 20,
        '', id='empty'),
    pytest.param(
        '<p>test</p>', 20,
        'test', id='short_text'),
    # Truncation
    pytest.param(
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla eget diam vel lectus ultrices commodo. Phasellus aliquet ultrices molestie. Vestibulum elementum sapien quis sapien vestibulum, sed dictum velit commodo. Donec blandit risus varius ex pulvinar, ac aliquet mi bibendum.</p>', 20,
        'Lorem ipsum dolor...', id='long_text'),
    pytest.param(
        'word word word word word', 24,
        'word word word word word', id='not_truncated_when_exactly_max_length'),
    pytest.param(
        'word word word word word', 23,
        'word word word word...', id='truncated_when_one_char_too_long'),
    pytest.param(
        'word word word word word word word word word word', 20,
        'word word word...', id='truncated_on_word_boundary'),
    pytest.param(
        'word word word word word word word word word word', 30,
        'word word word word word...', id='truncated_on_word_boundary_2'),
    pytest.param(
        'a' * 50, 20,
        'a' * 17 + '...', id='truncated_within_a_too_long_word'),
    pytest.param(
        '<p>First</p><p>Second and much more text</p>', 15,
        'First\nSecond...', id='truncated_after_line_return'),
])
def test_get_short_text(value, max_length, expected):
    result = html_utils.get_short_text(value, max_length=max_length)
    assert result == expected
    # The ellipsis is included in the length limit
    assert len(result) <= max_length
