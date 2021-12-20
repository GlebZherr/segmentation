#!/usr/bin/env python
import os, time, sys, sqlite3, re
from random import choice
from flask import Flask, render_template, url_for, request, redirect, \
    current_app, g, flash, jsonify, send_from_directory
from flask import session
# from flask_session import Session
# import urllib.request
# import urllib.error
# import urllib.parse
from urllib.parse import urlparse, urlunparse, unquote
# from lxml.html.clean import Cleaner
# from lxml import etree
from pprint import pprint

import logging
format = '%(asctime)s %(name)s %(threadName)s %(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=format)

sys.path.insert(0, '../lib')
import element
import http_get
from predictor import get_predictor, get_text_blocks

app = Flask(__name__)
# sess = Session()
app.debug = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['ENV'] = 'development'
app.secret_key = '4FjSQZVlzYfCZR1y5sFoU4Xy8bDmlarte5dfgHG'

# ------------------------------------------
# Variables
# ------------------------------------------
BLOCKS_DB = '../data/blocks.sqlite'
EXAMPLES_DB = '../data/examples.sqlite'
USER_AGENT = 'Mozilla/5.0 (compatible; YandexBlogs/0.99; robot; +http://yandex.com/bots)'
TIMEOUT = 30
predictor = get_predictor()

# ------------------------------------------
# Отключение кэширования статики
# ------------------------------------------
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


# @app.route('/bootstrap/<path:path>')
# def download_out_file(path):
#     return send_from_directory(OUT_DIR, path)

# ------------------------------------------
# Коннекты
# ------------------------------------------
def get_db(name):
    if name == 'blocks':
        db_name = BLOCKS_DB
    elif name == 'examples':
        db_name = EXAMPLES_DB
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(db_name)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ------------------------------------------
# Utils
# ------------------------------------------
def convert_from_punycode(uri):
    if 'xn--' in uri:
        o = urlparse(uri)
        puri = o.netloc.encode('utf8').decode('idna')
        return urlunparse(o._replace(netloc=puri))
    else:
        return uri

def get_domain(url):
    o = urlparse(url)
    return o.netloc


# ------------------------------------------------
# Главная страница
# ------------------------------------------------
@app.route('/')
def index():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        data['id_url'] = request.values.get('id_url', type=int, default=0)
        count_blocks = 0
        if data['id_url']:
            cur.execute("SELECT url FROM urls WHERE id_url=:id_url", {'id_url': data['id_url']})
            data['url'] = cur.fetchall()[0][0]
            cur.execute("SELECT count(1) FROM blocks WHERE id_url=:id_url", {'id_url': data['id_url']})
            count_blocks = cur.fetchall()[0][0]
            print(f'Blocks from BD {count_blocks}')

        # Список блоков, получение html-текста
        if 'url' in data:
            if count_blocks == 0:
                content = http_get.get_text(data['url'])
                cur.execute("UPDATE urls SET content=:content WHERE id_url=:id_url",
                            {'content': content, 'id_url': data['id_url']})
                conn.commit()

                tree = element.http_get_content(text=content.strip())
                blocks = element.get_text_blocks(tree)
                print(f'Blocks from Elements {len(blocks)}')
                for i, (text, tag, address) in enumerate(blocks):
                    cur.execute('''INSERT INTO blocks (id_url, tag, address, page_order, text, text_length)
                                   VALUES (:id_url, :tag, :address, :order, :text, :text_length)''',
                                   {'text': text,
                                    'tag': tag,
                                    'order': i,
                                    'address': address,
                                    'id_url': data['id_url'],
                                    'text_length': len(text)})
                conn.commit()

            cur.execute("SELECT id_block, label, tag, page_order, text FROM blocks WHERE id_url=:id_url",
                        {'id_url': data['id_url']})
            data['blocks'] = []
            for row in cur.fetchall():
                (id_block, label, tag, page_order, text) = row
                data['blocks'].append({'text': text.replace('\n', '<br>'),
                                       'tag': tag,
                                       'order': page_order,
                                       'id_block': id_block,
                                       'label': label})

    return render_template('index.j2', **data)


# ------------------------------------------------
# Examples
# ------------------------------------------------
@app.route('/examples', methods=['GET'])
def examples():
    data = {}
    with app.app_context():
        conn = get_db('examples')
        cur = conn.cursor()
        cur.execute('''SELECT domain, count(1) FROM pages WHERE result=1 GROUP BY domain ORDER BY domain''')

        domains = []
        for domain, count in cur.fetchall():
            domains.append({'name': domain, 'count': count})

        data['domains'] = domains
        # pprint(domains)

    return render_template('examples.j2', **data)


# ------------------------------------------------
# Example items
# ------------------------------------------------
@app.route('/example_items', methods=['GET'])
def example_items():
    data = {}
    with app.app_context():
        conn = get_db('examples')
        cur = conn.cursor()
        data['domain'] = request.values.get('domain', type=str)
        cur.execute('''SELECT id_page, url, content FROM pages WHERE domain=:domain AND result=1''',
                    {'domain': data['domain']})

        items = []
        for id_page, url, content in cur.fetchall():
            content = content.replace('\n', '<br>')
            items.append({'id_page': id_page, 'url': url, 'text': content})

        data['items'] = items

    return render_template('examples.j2', **data)


# ------------------------------------------------
# Получение блоков
# ------------------------------------------------
@app.route('/get_question', methods=['POST'])
def get_question():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        url = request.values.get('url', type=str, default='')
        url = url.strip()
        url = unquote(url)
        url = convert_from_punycode(url)
        url = re.sub(r'#.*', '', url)
        data['url'] = url
        cur.execute("SELECT id_url FROM urls WHERE url=:url", {'url': url})
        for row in cur.fetchall():
            data['id_url'] = row[0]
        if url and 'id_url' not in data:
            cur.execute("INSERT INTO urls (url, domain) VALUES (:url, :domain)",
                        {'url': data['url'], 'domain': get_domain(url)})
            conn.commit()
            data['id_url'] = cur.lastrowid

    return redirect(url_for('index', **data))


# ------------------------------------------------
# AJAX-запрос запись метки
# ------------------------------------------------
@app.route('/set_label', methods=['GET','POST'])
def set_label():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        id_block = request.values.get('id_block', type=int)
        checked = request.values.get('checked', type=str)
        name = request.values.get('name', type=str)
        if checked == 'false':
            cur.execute("UPDATE blocks SET label=:label WHERE id_block=:id_block",
                        {'label': None, 'id_block': id_block})
        else:
            cur.execute("UPDATE blocks SET label=:label WHERE id_block=:id_block",
                        {'label': name, 'id_block': id_block})
        conn.commit()
        print(f'{id_block} {name} {checked}')
        data['result'] = 'OK'

    return jsonify(data)


# ------------------------------------------------
# AJAX-запрос список всех сохраненных url-ов
# ------------------------------------------------
@app.route('/get_urls', methods=['GET','POST'])
def get_urls():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        cur.execute('''SELECT u.id_url,
                              u.url,
                              count(b.id_block) as count_blocks,
                              count(b.label) as count_labels
                        FROM urls u
                        LEFT JOIN blocks b ON u.id_url=b.id_url
                        GROUP BY u.id_url
                        ORDER BY u.id_url DESC''')
        data['sites'] = []
        for i, row in enumerate(cur.fetchall()):
            (id_url, url, count_blocks, count_labels) = row
            data['sites'].append({'id_url': id_url,
                                  'url': url,
                                  'count_blocks': count_blocks,
                                  'count_labels': count_labels,
                                  'n': i+1})

        cur.execute('''SELECT count(1) as count_blocks, count(b.label) as count_labels
                       FROM urls u JOIN blocks b ON u.id_url=b.id_url''')
        data['total_blocks'], data['total_labels'] = cur.fetchone()

    return jsonify(data)


# ------------------------------------------------
# AJAX-запрос получения предитктов блоков
# ------------------------------------------------
@app.route('/detect', methods=['GET'])
def detect():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        id_url = request.values.get('id_url', type=int)
        cur.execute('''SELECT content FROM urls WHERE id_url=:id_url''', {'id_url': id_url})
        content = cur.fetchone()[0]
        labels = predictor(content)
        scores = predictor(content, 'scores')
        data['labels'] = labels.tolist()
        data['scores'] = scores.to_dict(orient='records')

    return jsonify(data)


# ------------------------------------------------
# Очистка блоков для старницы
# ------------------------------------------------
@app.route('/clear_page', methods=['GET'])
def clear_page():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        id_url = request.values.get('id_url', type=int)
        cur.execute('''DELETE FROM blocks WHERE id_url=:id_url''', {'id_url': id_url})
        conn.commit()
        data['id_url'] = id_url

    return redirect(url_for('index', **data))


# ------------------------------------------------
# Удаление страницы полностью из базы
# ------------------------------------------------
@app.route('/delete_page', methods=['GET'])
def delete_page():
    data = {}
    with app.app_context():
        conn = get_db('blocks')
        cur = conn.cursor()
        id_url = request.values.get('id_url', type=int)
        cur.execute('''DELETE FROM blocks WHERE id_url=:id_url''', {'id_url': id_url})
        cur.execute('''DELETE FROM urls WHERE id_url=:id_url''', {'id_url': id_url})
        conn.commit()

    return redirect(url_for('index', **data))


# ------------------------------------------------
# Запуск локального девел-сервера
# ------------------------------------------------
if __name__ == '__main__':
    # sess.init_app(app)
    app.debug = True
    app.run(port=8000, host='0.0.0.0', processes=4, threaded=False)

    # sshtunnel -vtn -U tumanov_g -P tumanov_g -R 192.130.30.2:8000 -L 127.0.0.1:33000 -- 45.89.225.145
    # screen jupyter lab --no-browser --ip 0.0.0.0 --port 10017
    # jupyter lab list
    # http://45.89.225.145:10017/?token=1dc6d66b7fa67285bf8e532330d54a492753b89af96145ff
