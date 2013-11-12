#!/usr/bin/env python
# -*- coding: utf-8 -*-
##----------------------------------------------------------------------------------
## Translations utility functions
##----------------------------------------------------------------------------------


# get_text_for_lang function
#-----------------------------------------------------------------------------------
def get_text_for_lang(text, lang='en'):
    if not text:
        return ''
    if '|||' in text:
        index = text.index('|||')
        if lang == 'fr':
            return text[index+3:]
        else:
            return text[:index]
    else:
        return text

# get_html_text_for_lang function
#-----------------------------------------------------------------------------------
def get_html_text_for_lang(text, lang='en'):
    if not text:
        return ''
    if '<p>|||</p>' in text:
        index = text.index('<p>|||</p>')
        if lang == 'fr':
            return text[index+10:]
        else:
            return text[:index]
    else:
        return text

