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
    assert html_utils.clean_html_tags(value, allow_iframes=allow_iframes, extra_allowed_attrs={'iframe': {'data-custom'}}) == expected
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
    assert sorted(html_utils.ALLOWED_ATTRS.keys()) == ['*', 'a', 'div', 'iframe', 'img', 'source', 'td', 'th', 'video']


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
    assert html_utils.get_short_text(value, max_length=max_length, margin=margin) == expected
