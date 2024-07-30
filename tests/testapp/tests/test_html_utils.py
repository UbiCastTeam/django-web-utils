import pytest
from django_web_utils import html_utils


@pytest.mark.parametrize('value,allow_iframes,expected', [
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe>', False,
        '&lt;iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"&gt;&lt;/iframe&gt;', id='escape_iframe'),
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe>', True,
        '<iframe allow="autoplay"></iframe>', id='escape_iframe_src'),
    pytest.param(
        '<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg==" allow="autoplay" nope="test"></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', True,
        '<iframe allow="autoplay"></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', id='escape_multiple'),
    pytest.param(
        '<iframe src="https://localhost/test" allow="autoplay" nope="test"></iframe>', True,
        '<iframe src="https://localhost/test" allow="autoplay"></iframe>', id='https_iframe_src'),
    pytest.param(
        '<img src="data:image/png;base64,ABCD" style="width: 50%">', False,
        '<img src="data:image/png;base64,ABCD" style="width: 50%;">', id='conserve_base64_image'),
    pytest.param(
        '<a href="data:image/png;base64,ABCD">', False,
        '<a></a>', id='clean_a_base64_href'),
    pytest.param(
        '<a href="http://google.com" style="font-size: 75%"></a>', False,
        '<a href="http://google.com" style="font-size: 75%;"></a>', id='conserve_a_http_href'),
])
def test_clean_html_tags(value, allow_iframes, expected):
    iframe = html_utils.clean_html_tags(value, allow_iframes=allow_iframes)
    assert iframe == expected
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
        '<div data-name="the name">Sample</div>', None,
        '<div>Sample</div>', id='default_allowed_attrs'),
    pytest.param(
        '<div data-name="the name">Sample</div>', {'div': {'data-name'}},
        '<div data-name="the name">Sample</div>', id='allow_data_name_attr'),
])
def test_clean_html_tags__extra_attrs(value, extra_allowed_attrs, expected):
    iframe = html_utils.clean_html_tags(value, extra_allowed_attrs=extra_allowed_attrs)
    assert iframe == expected
    assert sorted(html_utils.ALLOWED_ATTRS.keys()) == ['*', 'a', 'img', 'source', 'td', 'th', 'video']


@pytest.mark.parametrize('value,max_length,margin,expected', [
    pytest.param(
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', 20, 0,
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', id='keep_tags'),
    pytest.param(
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', 20, 100,
        '', id='return_nothing_if_short_text_not_needed'),
    pytest.param(
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla eget diam vel lectus ultrices commodo. Phasellus aliquet ultrices molestie. Vestibulum elementum sapien quis sapien vestibulum, sed dictum velit commodo. Donec blandit risus varius ex pulvinar, ac aliquet mi bibendum.</p>', 20, 0,
        '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>Lorem ipsum dolor ...</p>', id='short_long_string'),
])
def test_get_short_text(value, max_length, margin, expected):
    short_html = html_utils.get_short_text(value, max_length=max_length, margin=margin)
    assert short_html == expected
