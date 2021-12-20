#!/usr/bin/env python
import sqlite3
import sys

import pandas as pd
from fastai.basics import progress_bar

sys.path.insert(0, '../lib')
from get_features import get_features


DATABASE_FILE = '../data/blocks.sqlite'
COLUMNS_FILE = '../data/columns.csv'
OUTPUT_FILE = '../../data/features.json.gzip'
DROPCOLS_FILE = '../data/drop_cols.csv'
DROP_THRESHOLD = 0.004


pd.options.display.float_format = lambda x: f'{x:0.3g}'
pd.options.display.max_rows = 100

all_features = []

with sqlite3.connect(DATABASE_FILE) as conn:
    cur1 = conn.cursor()
    cur2 = conn.cursor()

    cur1.execute("SELECT count(1) FROM urls")
    total = cur1.fetchone()[0]

    cur1.execute("SELECT id_url, domain, content FROM urls")
    # cur1.execute("SELECT id_url, content FROM urls WHERE id_url >= (abs(random()) % (SELECT max(id_url) FROM urls)) LIMIT 1")
    print('Start page processing:')
    for id_url, domain, content in progress_bar(cur1.fetchall(), total=total):
        # print(id_url)
        cur2.execute("SELECT id_block, label, address FROM blocks WHERE id_url=:id_url",
                     {'id_url': id_url})
        labels = {}
        for id_block, label, address in cur2.fetchall():
            labels[address] = (id_block, label)

        features = get_features(content, labels)
        for row in features:
            row['domain'] = domain
            row['url'] = id_url
        all_features.extend(features)

print()

df_features = pd.DataFrame.from_records(all_features)
# ------------------------
# drop rare
drop_count = int(df_features.shape[0] * DROP_THRESHOLD)
drop_cols = df_features.columns[df_features.count() < drop_count].values
df_features = df_features.drop(drop_cols, 1)

drop_df = pd.DataFrame(drop_cols, columns=['col_name'])
drop_df.to_csv(DROPCOLS_FILE, index=False)
# ------------------------
# ma_num_chars
df_features['ma_num_chars'] = df_features.groupby('url')['self_num_chars'] \
    .transform(lambda s: (s/s.max()).rolling(5, min_periods=1, center=True).mean())
# ------------------------
print(df_features.sample(1).T)
print(df_features.shape)

col_df = pd.DataFrame(df_features.columns, columns=['col_name'])
col_df.to_csv(COLUMNS_FILE, index=False)

df_features.to_json(OUTPUT_FILE, force_ascii=False, orient='records', lines=True, compression='gzip')
print(f"Save file: {OUTPUT_FILE}")
print(df_features.label.value_counts(dropna=False))

