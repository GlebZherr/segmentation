import urllib3
urllib3.disable_warnings()
import urllib.request
import urllib.error
import requests, re
from lxml import html
from lxml import etree
from lxml.html.clean import Cleaner
import element


USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.52 Safari/537.36'
TIMEOUT = 40
HEADERS = {'User-Agent': USER_AGENT,
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Language': 'ru'}


def remove_on_attributes(tree):
    jsreg = re.compile(r'^on\w+$', flags=re.I)
    for elem in tree.iter(tag=etree.Element):
        for attr in elem.keys():
            if jsreg.search(attr):
                del elem.attrib[attr]


def get_charset_from_meta(content):
    charset_res = re.search(r'<meta.*?charset=["\']*(.+?)["\'>]', content, flags=re.I)
    if charset_res:
        return charset_res.group(1)
    pragma_res  = re.search(r'<meta.*?content=["\']*;?charset=(.+?)["\'>]', content, flags=re.I)
    if pragma_res:
        return pragma_res.group(1)
    xml_res     = re.search(r'^<\?xml.*?encoding=["\']*(.+?)["\'>]', content, flags=re.I)
    if xml_res:
        return xml_res.group(1)


def _clean_html(text):
    cleaner = Cleaner(
        scripts             = True,
        javascript          = True,
        comments            = True,
        style               = True,
        inline_style        = False,
        links               = False,
        meta                = False,
        page_structure      = False,
        embedded            = True,
        frames              = True,
        forms               = False,
        annoying_tags       = False,
        remove_unknown_tags = False,
        safe_attrs_only     = False,
        add_nofollow        = False,
        remove_tags         = ['svg', 'symbol', 'g'],
        allow_tags          = None,
        kill_tags           = ['iframe', 'script', 'svg', 'air-settings', 'textarea', 'style'],
    )
    return cleaner.clean_html(text)


def http_get_content(url=None, file=None, remove_scripts=False, base_url=None):
    if url:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        if r.encoding is None or r.encoding == 'ISO-8859-1':
            encoding = get_charset_from_meta(r.text)
            r.encoding = encoding
        if r.encoding.upper() == 'CP-1251':
            r.encoding = 'windows-1251'
        text = r.text
        text = re.sub(r'<\?xml .* \?>', '', text, flags=re.X)
    elif file:
        text = file.read()
        text = re.sub(r'<\?xml .* \?>', '', text, flags=re.X + re.I)
        try:
            tree = html.fromstring(text)
        except:
            return None
        text = html.tostring(tree, encoding='unicode')
    else:
        raise ParamError('Argument "url" or "file" needed')

    if remove_scripts:
        text = _clean_html(text)

    tree = html.fromstring(text)

    for meta in tree.findall('.//meta'):
        if 'charset' in meta.get('content', ''):
            meta.clear()
    try:
        tree.find('.//head').insert(0, etree.Element('meta', charset='utf-8'))
    except:
        pass

    if base_url is not None:
        tree.make_links_absolute(base_url)
    # remove_on_attributes(tree)
    return tree


def get_text(url):
    tree = http_get_content(url=url, remove_scripts=True)
    text = etree.tostring(tree, encoding='unicode', method='html')
    return text
