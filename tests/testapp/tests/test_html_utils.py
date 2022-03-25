import pytest

from django_web_utils.html_utils import clean_html_tags, get_short_text


@pytest.mark.parametrize('value,allow_iframes,expected', [
    pytest.param('<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg=="></iframe>', False, '&lt;iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg=="&gt;&lt;/iframe&gt;', id='escape_iframe'),
    pytest.param('<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg=="></iframe>', True, '<iframe></iframe>', id='escape_iframe_src'),
    pytest.param('<iframe src="data:text/html;base64,PHNjcmlwdD5hbGVydCgiWFNTIik7PC9zY3JpcHQ+Cg=="></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', True, '<iframe></iframe><img src="data:image/png;base64,ABCD"><a href="http://google.com"></a>', id='escape_multiple'),
    pytest.param('<img src="data:image/png;base64,ABCD">', False, '<img src="data:image/png;base64,ABCD">', id='conserve_base64_image'),
    pytest.param('<a href="data:image/png;base64,ABCD">', False, '<a></a>', id='clean_a_base64_href'),
    pytest.param('<a href="http://google.com"></a>', False, '<a href="http://google.com"></a>', id='conserve_a_http_href')
])
def test_clean_html_tags(value, allow_iframes, expected):
    iframe = clean_html_tags(value, allow_iframes=allow_iframes)
    assert iframe == expected


@pytest.mark.parametrize('value,max_length,margin,expected', [
    pytest.param('<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', 20, 0, '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', id='keep_tags'),
    pytest.param('<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>test</p>', 20, 100, '', id='return_nothing_if_short_text_not_needed'),
    pytest.param('<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nulla eget diam vel lectus ultrices commodo. Phasellus aliquet ultrices molestie. Vestibulum elementum sapien quis sapien vestibulum, sed dictum velit commodo. Donec blandit risus varius ex pulvinar, ac aliquet mi bibendum.</p>', 20, 0, '<p><img src="data:image/png;base64,//fVYAExERERERERERERERjWOXJADu+UiLno+0l+LQRBSjhoYGNDQ0X"/>Lorem ipsum dolor ...</p>', id='short_long_string')
])
def test_get_short_text(value, max_length, margin, expected):
    short_html = get_short_text(value, max_length=max_length, margin=margin)
    assert short_html == expected
