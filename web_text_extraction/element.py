#!/usr/bin/env python
# -*- coding: utf-8 -*-
import urllib3
urllib3.disable_warnings()
import regex as re
from lxml import etree, html
import hashlib

# Утилита get_text_blocks - на вход получает содержимое html документа
# на выходе - список одностроковых текстов на блок.

# Минимальное количество символов в блоке (меньше не берем)
MIN_CHAR_LENTH = 1

# Минимальное количество слов в блоке
MIN_WORD_LENTH = 1

# --------------------------------------------------------------------------------------------------
SKIP_TAGS = set('script style link meta noscript select option button html input skip'.split())
NOSPLIT_TAGS = set('a abbr acronym b br big del em font i ins small strike strong sub sup u span nobr noindex'.split())
# --------------------------------------------------------------------------------------------------

PAT1 = re.compile(r'([A-ZА-ЯЁa-zа-яё0-9]) ([\)\]»\}\!\?\.,;%])')
PAT2 = re.compile(r'([\(\[«\{]) ([A-ZА-ЯЁa-zа-яё0-9])')
PAT_BR = re.compile(r'<br>')
PAT3 = re.compile(r'\s+(<br>)')
PAT4 = re.compile(r'(<br>)\s+')
HRE = re.compile(r'^h([1-6])$')
PAT5 = re.compile(r'(<br>){3,}')


def _siblings_index(e):
    count_before = sum([1 for s in e.itersiblings(e.tag, preceding=True)])
    count_after  = sum([1 for s in e.itersiblings(e.tag)])
    indx = ''
    if count_before > 0 or count_after > 0:
        indx = '[%d]' % count_before
    return indx


def addr(e, ashash=False):
    address = []
    for a in e.iterancestors():
        address.append(a.tag + _siblings_index(a))
    address.reverse()
    address.append(e.tag + _siblings_index(e))
    addr = '::'.join(address)
    if ashash:
        m = hashlib.md5()
        m.update(addr.encode('utf8'))
        return m.hexdigest()
    else:
        return(addr)


def fold_space(text):
    text = text.strip()
    text = ' '.join(text.split())
    if text:
        text = re.sub(PAT3, r'\1', text)
        text = re.sub(PAT4, r'\1', text)
        text = re.sub(PAT5, '<br><br>', text)
    return text


def iter_text(elem, it=0):
    if elem.tag == 'br':
        yield '<br>'
    yield elem.text
    for child in elem.iterchildren(tag=etree.Element):
        yield from iter_text(child, it+1)
        yield child.tail


def get_text(e):
    # Если тег из SKIP_TAGS, то внутренний текст не берем, иначе - берем
    texts = []
    if e.tag not in SKIP_TAGS and e.text:
        texts.append(e.text)

    # htags = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}

    # Цикл по всем прямым потомкам
    for c in e.iterchildren(tag=etree.Element):

        # Если встретился дочерний тег - неблоковый, то берем текст внутри
        if c.tag in NOSPLIT_TAGS:

            if any(x.tag not in NOSPLIT_TAGS for x in c.iter(tag=etree.Element)):
                texts.append(get_text(c)[0])
            else:
                # texts.append(' '.join(t for t in c.itertext()))
                for text in iter_text(c):
                    if text and text.split():
                        texts.append(text)

        # Берем хвост у всех тегов
        if c.tail is not None:
            texts.append(c.tail)

    return (fold_space(' '.join(texts)), addr(e))


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


def http_get_content(text=None):
    # text = re.sub(r'<\?xml .* \?>', '', text, flags=re.X + re.I)
    tree = html.fromstring(text)
    return tree


def get_text_blocks(tree, elements=False):
    blocks = []
    for elem in tree.iter(tag=etree.Element):
        if elem.tag not in NOSPLIT_TAGS:
            text, address = get_text(elem)
            if text and len(text.split()) > 0:
                text = re.sub(PAT1, r'\1\2', text)
                text = re.sub(PAT2, r'\1\2', text)
                text = re.sub(PAT_BR, '\n', text)
                text = text.strip()
                if text:
                    if elements:
                        blocks.append((text, elem.tag, address, elem))
                    else:
                        blocks.append((text, elem.tag, address))
    return blocks


# --------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    import http_get

    url = 'https://e-news.su/mnenie-i-analitika/387920-rusofobija-brjusselja-bet-bumerangom-po-es.html'

    content = '''<div itemprop="articleSection" class="full-story-text"><div style="text-align:center;"></div><br><span class="masha_index masha_index6" rel="6"></span>При наличии дачного участка данный вид бизнеса может стать расширением любимого хобби. Но для выхода на оптовые поставки, стоит задуматься о значительном расширении теплиц и вложении средств. Хотя государство активно помогает сельскохозяйственной сфере, поэтому можно рассчитывать на субсидии и льготы. Оптимально иметь хотя бы средние знания в выращивании различных культур. На первых порах не стоит браться за производство экзотической продукции, так как есть шанс потерять все вложения.<br><br><h2><span class="masha_index masha_index7" rel="7"></span>Разновидности бизнеса<br></h2><span class="masha_index masha_index8" rel="8"></span>Прежде чем направиться в НФС для регистрации бизнеса и закупать оборудование, стоит определиться с видом продукции, на которую будет сделан упор:<br><span class="masha_index masha_index9" rel="9"></span>•    цветы — выращивание цветов на срез имеет более высокую рентабельность, чем остальные виды, но при этом требует вложений в 4 раза больше и знаний;<br><span class="masha_index masha_index10" rel="10"></span>•  зелень — идеальный вариант для новичков, тем более реализовывать товар можно напрямую покупателям;<br><span class="masha_index masha_index11" rel="11"></span>• овощи — можно остановиться на традиционных огурцах и томатах, на них не спадает спрос никогда, а при наличии договоренности с рестораном или сетью кафе, можно расшириться на более редкие сорта;<br><span class="masha_index masha_index12" rel="12"></span>•  экзотика — подходит только для опытных садоводов, и только при реальном наличии спроса, к данной сфере относятся все культуры, которые не характерны для региона.<br><br><h2><span class="masha_index masha_index13" rel="13"></span>Техническое оснащение<br></h2><span class="masha_index masha_index14" rel="14"></span>Самым главным элементом на участке должна стать теплица. Причем стоит отдать предпочтение поликарбонатным моделям, которые выигрывают у остальных видов (стеклянных и пленочных) производительностью, светопропускаемостью, прочностью и ремонтопригодностью. Нелишним будет под теплицей предусмотреть наличие настила или даже фундамента, если планируется ставить обогрев и поставлять овощи круглый год. Кроме самой теплицы, понадобится:<br><span class="masha_index masha_index15" rel="15"></span>• система полива — оптимально установить капельное орошение, оно менее дорогостоящее, но при этом позволяет автоматизировать момент подачи воды;<br><span class="masha_index masha_index16" rel="16"></span>• освещение и отопление — потребуется для регионов, в которых затяжное межсезонье, а также есть риск частых заморозков;<br><span class="masha_index masha_index17" rel="17"></span>•  инвентарь.<br><span class="masha_index masha_index18" rel="18"></span>Стоит отметить, что существует несколько вариантов выращивания с/х продукции. Так, наиболее производительным является использование гидропоники, урожайность тогда превышает традиционный способ в 2-3 раза. Но теряются вкусовые качества, так что в некоторых случаях стоит остаться верным традиционному выращиванию в почве. Средний показатель рентабельности достигает 15-25%, но в зависимости от вида выращиваемой продукции значения могут варьироваться. Окупаемости стоит ждать через 1-2 года.<br> <br></div>'''
    # content = open(file).read()
    # content = http_get.get_text(url)
    content = '''
<div class="article-content">
<p><span style="font-size: 12.16px;">По данным на 10 июля 2021 года в Астраханской области вакцинировано от коронавирусной инфекции 210079 человек (оба этапа иммунизации прошли 142850 человек). За период прививочной кампании в регион поступило 233762 дозы вакцины «Гам КОВИД Вак», 6070 доз вакцины «ЭпиВакКорона» и 830 доз вакцины «КовиВак».</span></p>
<p />За минувшие сутки зафиксировано 215 новых случаев заражения коронавирусной инфекцией.
</p>
<p>Всего с начала пандемии в Астраханской области зарегистрировано 38104 случая заражения COVID-19. Скончался 901 человек.<span style="font-size: 12.16px;"> </span></p>
<p>В стационарах, перепрофилированных для лечения пациентов с коронавирусной инфекцией, проходит лечение 941 человек (свободно 28% коечного фонда). На амбулаторном лечении находится 3121 человек.</p>
<p>Коэффициент распространения инфекции – 1,26.</p></div>
    '''

    tree = http_get_content(text=content)
    blocks = get_text_blocks(tree, elements=True)

    # print('\n-----------------\n'.join([r[0] for r in blocks]))

    for block, tag, address, elem in blocks:
        print('-' * 80)
        print(tag, elem.attrib.get('class'))
        print(block)

    # print('=' * 80)
    # print(etree.tostringlist(tree, method="xml", encoding="unicode"))
