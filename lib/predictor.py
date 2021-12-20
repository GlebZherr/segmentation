#!/usr/bin/env python
from pprint import pprint

import pandas as pd
from catboost import CatBoostClassifier

import element
import http_get
from get_features import get_features

DATABASE_FILE = '../data/blocks.sqlite'
MODEL_FILE = '../data/model_weights_sqrt.cbm'
COLUMN_FILE = '../data/columns.csv'
DROPCOLS_FILE = '../data/drop_cols.csv'


def get_text_blocks(content):
    tree = element.http_get_content(text=content)
    blocks = element.get_text_blocks(tree)
    return blocks


def get_predictor():
    model = CatBoostClassifier()
    model.load_model(MODEL_FILE)
    columns = pd.read_csv(COLUMN_FILE).col_name.tolist()
    drop_cols = pd.read_csv(DROPCOLS_FILE).col_name.tolist()

    categorical_cols = ['self_tag', 'parent_tag', 'grand_parent_tag',
                        'right_tag', 'left_tag']

    text_cols = ['self_class', 'parent_class', 'grand_parent_class',
                 'right_class', 'left_class', 'grand_parent_id', 'left_id',
                 'parent_id', 'right_id', 'self_id','grand_parent_itemprop',
                 'left_itemprop', 'parent_itemprop', 'right_itemprop',
                 'self_itemprop']

    def predict_labels(content, type='labels'):
        features = get_features(content)
        data = pd.DataFrame.from_records(features, columns=columns)
        data = data.set_index('id')
        data = data.drop(drop_cols, 1, errors='ignore')
        data['ma_num_chars'] = data['self_num_chars'] / data['self_num_chars'].max()
        data['ma_num_chars'] = data['ma_num_chars'].rolling(5, min_periods=1, center=True).mean()
        data = data.drop(['label', 'text', 'url', 'order', 'domain'], 1, errors='ignore')
        data[categorical_cols] = data[categorical_cols].fillna('NA')
        data[text_cols] = data[text_cols].fillna('')
        if type == 'labels':
            preds = model.predict(data)[:, 0]
            return preds
        else:
            scores_proba = model.predict_proba(data)
            scores = data[[]].copy()
            scores[[*model.classes_]] = scores_proba
            return scores

    return predict_labels


if __name__ == '__main__':

    predictor = get_predictor()

    url = 'https://ria.ru/20210626/izmeneniya-1738711523.html'
    content = http_get.get_text(url)
    labels = predictor(content)
    scores = predictor(content, 'scores')

    blocks = get_text_blocks(content)
    for i, (text, _, _) in enumerate(blocks):
        print(text)
        print(labels[i])
        pprint(scores.iloc[i].to_dict())
        print('-' * 80)

