#!/usr/bin/env python
import os, time, sys, sqlite3
from pprint import pprint
from random import choice
import urllib.request
import urllib.error
import urllib.parse
from lxml.html.clean import Cleaner
from lxml import etree, html
import regex as re
import pandas as pd
from razdel import sentenize
from itertools import takewhile

sys.path.insert(0, '.')
import element
import http_get


def get_text_blocks(content):
    tree = element.http_get_content(text=content)
    blocks = element.get_text_blocks(tree)
    return blocks


def get_inner_tags(elem):
    for c in elem.iterchildren():
        text = []
        for t in c.itertext():
            text.append(t.strip())
        text = ' '.join(text)
        yield c.tag, text
        yield from get_inner_tags(c)


def get_attr_processor(type_attr='class'):
    if type_attr == 'class':
        reg = re.compile(r"[a-z0-9-]+")
    else:
        reg = re.compile(r"[a-z]+")
    def process_text(text):
        if not text:
            return ''
        text = text.lower()
        text = ' '.join(text.split())
        words = re.findall(reg, text)
        text = ' '.join(words)
        return text
    return process_text


def get_element_info(elem, prefix):
    stat = {}
    stat[f'{prefix}_tag'] = elem.tag
    stat[f'{prefix}_index'] = sum([1 for s in elem.itersiblings(elem.tag, preceding=True)])
    stat[f'{prefix}_class'] = class_processor(elem.attrib.get('class'))
    stat[f'{prefix}_itemprop'] = class_processor(elem.attrib.get('itemprop'))
    stat[f'{prefix}_id'] = id_processor(elem.attrib.get('id'))
    return stat


def get_sentences_function():
    re_words = re.compile(r'\b [\p{L}\p{N}] [\p{L}\p{N}-]* [\p{L}\p{N}]* \b', re.X)
    def get_sentences_info(text, prefix='self'):
        stat = {}
        sentences = [sent.text for sent in sentenize(text)]
        words = re.findall(re_words, text)
        stat[f'{prefix}_sentences_count'] = len(sentences)

        if sentences:
            stat[f'{prefix}_sentences_avg_chars'] = \
                sum(len(sent) for sent in sentences) / len(sentences)

        if words:
            stat[f'{prefix}_sentences_avg_words'] = \
                sum(len(re.findall(re_words, sent)) for sent in sentences) / len(words)

        if text:
            stat[f'{prefix}_full_stop'] = 1 if text[-1] in '’”.!?:' else 0
            stat[f'{prefix}_start_bullet'] = 1 if text[0] in '—•⁃-' else 0

        return stat
    return get_sentences_info


def get_inner_stat_function():
    # re_find_words = re.compile(r'[\w][\w.-]*[\w]*')
    re_words = re.compile(r'\b [\p{L}\p{N}] [\p{L}\p{N}-]* [\p{L}\p{N}]* \b', re.X)

    def gather_inner_stat(elem, outer_text):
        stat = {}
        o_chars = len(''.join(outer_text.split()))
        o_words = len(re.findall(re_words, outer_text))
        a_text_list, a_count = [], 0
        b_text_list, b_count = [], 0
        t_text_list, t_count = [], 0
        e_text_list, e_count = [], 0
        i_count = 0
        r_count = 0

        for tag, inner_text in get_inner_tags(elem):
            if tag == 'a':
                a_text_list.append(inner_text)
                a_count += 1
            elif tag in ['b', 'strong']:
                b_text_list.append(inner_text)
                b_count += 1
            elif tag in ['i', 'em']:
                e_text_list.append(inner_text)
                e_count += 1
            elif tag in ['img', 'svg']:
                i_count += 1
            elif tag == 'br':
                r_count += 1
            else:
                t_text_list.append(inner_text)
                t_count += 1

        a_text = ' '.join(a_text_list)
        a_chars = len(''.join(a_text.split()))
        a_words = len(re.findall(re_words, a_text))

        b_text = ' '.join(b_text_list)
        b_chars = len(''.join(b_text.split()))
        b_words = len(re.findall(re_words, b_text))

        t_text = ' '.join(t_text_list)
        t_chars = len(''.join(t_text.split()))
        t_words = len(re.findall(re_words, t_text))

        e_text = ' '.join(e_text_list)
        e_chars = len(''.join(e_text.split()))
        e_words = len(re.findall(re_words, e_text))

        stat['inner_anchor_chars_pc'] = 0
        stat['inner_bold_chars_pc'] = 0
        stat['inner_tags_chars_pc'] = 0
        stat['inner_italic_chars_pc'] = 0
        if o_chars > 0:
            stat['inner_anchor_chars_pc'] = a_chars / o_chars
            stat['inner_bold_chars_pc'] = b_chars / o_chars
            stat['inner_tags_chars_pc'] = t_chars / o_chars
            stat['inner_italic_chars_pc'] = e_chars / o_chars

        stat['inner_anchor_words_pc'] = 0
        stat['inner_bold_words_pc'] = 0
        stat['inner_tags_words_pc'] = 0
        stat['inner_italic_words_pc'] = 0
        if o_words > 0:
            stat['inner_anchor_words_pc'] = a_words / o_words
            stat['inner_bold_words_pc'] = b_words / o_words
            stat['inner_tags_words_pc'] = t_words / o_words
            stat['inner_italic_words_pc'] = e_words / o_words

        stat['inner_anchors'] = a_count
        stat['inner_bolds'] = b_count
        stat['inner_tags'] = t_count
        stat['inner_italic'] = e_count

        stat['inner_anchor_chars'] = a_chars
        stat['inner_bold_chars'] = b_chars
        stat['inner_tags_chars'] = t_chars
        stat['inner_italic_chars'] = e_chars

        stat['inner_anchor_words'] = a_words
        stat['inner_bold_words'] = b_words
        stat['inner_tags_words'] = t_words
        stat['inner_italic_words'] = e_words

        stat['inner_images'] = i_count
        stat['inner_br'] = r_count

        return stat

    return gather_inner_stat


def get_text_stat_function():
    re_words = re.compile(r'\b [\p{L}\p{N}] [\p{L}\p{N}-]* [\p{L}\p{N}]* \b', re.X)
    re_punkt = re.compile(r'\p{P}')
    re_upper = re.compile(r'\p{Lu}')
    re_lower = re.compile(r'\p{Ll}')
    re_digit = re.compile(r'\p{N}')
    re_other = re.compile(r'[^ \p{N} \p{L} \p{P} \p{Z} ]', re.X)
    def gather_stat(text, prefix):
        stat = {}
        chars = len(''.join(text.split()))
        words = re.findall(re_words, text)
        n_words = len(words)

        if chars > 0:
            chars_upper = len(re.findall(re_upper, text))
            chars_lower = len(re.findall(re_lower, text))
            chars_digit = len(re.findall(re_digit, text))
            chars_punct = len(re.findall(re_punkt, text))
            chars_other = len(re.findall(re_other, text))

            stat[f'{prefix}_upper_chars'] = chars_upper / chars
            stat[f'{prefix}_lower_chars'] = chars_lower / chars
            stat[f'{prefix}_digit_chars'] = chars_digit / chars
            stat[f'{prefix}_punct_chars'] = chars_punct / chars
            stat[f'{prefix}_other_chars'] = chars_other / chars

        if n_words > 0:
            stat[f'{prefix}_avg_word_length'] = sum(len(x) for x in words) / n_words

        stat[f'{prefix}_num_chars'] = chars
        stat[f'{prefix}_num_words'] = n_words
        return stat
    return gather_stat


def get_path(address):
    path = []
    for t in address.split('::')[:-1]:
        tag = t.split('[')[0]
        path.append(tag)
    return path


def get_features(content, labels=None):
    tree = element.http_get_content(text=content)
    blocks = element.get_text_blocks(tree, elements=True)
    check_tags = ['aside', 'footer', 'form', 'li', 'nav']
    features = []

    max_level = 0
    for order, (text, _, address, elem) in enumerate(blocks):
        data_row = {}
        if labels is not None:
            data_row['id'], data_row['label'] = labels[address]
        else:
            data_row['id'], data_row['label'] = order, None
        # data_row['text'] = text
        data_row['order'] = order
        addr_tags = set(get_path(address))
        for tag in check_tags:
            data_row[f"in_path_{tag}"] = int(tag in addr_tags)

        data_row.update(get_element_info(elem, 'self'))
        data_row.update(text_stat(text, 'self'))
        data_row.update(inner_stat(elem, text))
        data_row.update(sentences_info(text, 'self'))

        _prev = elem.getprevious()
        if _prev is not None:
            data_row.update(get_element_info(_prev, 'left'))
            _prev_text, _ = element.get_text(_prev)
            data_row.update(text_stat(_prev_text, 'left'))
            data_row.update(sentences_info(_prev_text, 'left'))

        _next = elem.getnext()
        if _next is not None:
            data_row.update(get_element_info(_next, 'right'))
            _next_text, _ = element.get_text(_next)
            data_row.update(text_stat(_next_text, 'right'))
            data_row.update(sentences_info(_next_text, 'right'))

        try:
            parent = next(elem.iterancestors())
            data_row.update(get_element_info(parent, 'parent'))
            parent_text, _ = element.get_text(parent)
            data_row.update(text_stat(parent_text, 'parent'))
            try:
                grand_parent = next(parent.iterancestors())
                data_row.update(get_element_info(grand_parent, 'grand_parent'))
                grand_parent_text, _ = element.get_text(grand_parent)
                data_row.update(text_stat(grand_parent_text, 'grand_parent'))
            except StopIteration:
                pass
        except StopIteration:
            pass

        data_row['same_as_left'] = 1 if data_row.get('left_tag', '.') == data_row['self_tag'] else 0
        data_row['same_as_right'] = 1 if data_row.get('right_tag', '.') == data_row['self_tag'] else 0

        features.append(data_row)

    for i, row in enumerate(features):
        row['relative_position'] = (i+1) / len(features)
        row['absolute_position'] = i

    return features


text_stat = get_text_stat_function()
inner_stat = get_inner_stat_function()
class_processor = get_attr_processor('class')
id_processor = get_attr_processor('id')
sentences_info = get_sentences_function()


if __name__ == '__main__':


    pd.options.display.float_format = lambda x: f'{x:0.3g}'
    pd.options.display.max_rows = 1000

    all_features = []
    columns = set()

    DATABASE_FILE = '../data/blocks.sqlite'
    COLUMNS_FILE = '../data/columns.csv'

    with sqlite3.connect(DATABASE_FILE) as conn:
        cur1 = conn.cursor()
        cur2 = conn.cursor()

        # cur1.execute("SELECT id_url, content FROM urls")
        cur1.execute("SELECT id_url, content FROM urls WHERE id_url >= (abs(random()) % (SELECT max(id_url) FROM urls)) LIMIT 1")
        # cur1.execute("SELECT id_url, content FROM urls WHERE id_url=459")
        for id_url, content in cur1.fetchall():
            print(id_url)
            cur2.execute("SELECT id_block, label, address FROM blocks WHERE id_url=:id_url",
                         {'id_url': id_url})
            labels = {}
            for id_block, label, address in cur2.fetchall():
                labels[address] = (id_block, label)

            features = get_features(content, labels)
            for row in features:
                columns.update(row.keys())
            all_features.extend(features)

    # columns = pd.read_csv(COLUMNS_FILE).col_name.tolist()
    df_deatures = pd.DataFrame.from_records(all_features, columns=sorted(columns))
    print(df_deatures.sample(1).T)
    print(df_deatures.shape)
    # itemprop_cols = [c for c in df_deatures.columns if '_id' in c]
    # print(df_deatures[itemprop_cols].sample(1).T)
    sys.exit(0)

    col_df = pd.DataFrame(sorted(columns), columns=['col_name'])
    col_df.to_csv(COLUMNS_FILE, index=False)

    save_file_json = 'features.json.gzip'
    df_deatures.to_json(save_file_json, force_ascii=False, orient='records', lines=True, compression='gzip')
    print(f"Save file: {save_file_json}")
    print(df_deatures.label.value_counts(dropna=False))
