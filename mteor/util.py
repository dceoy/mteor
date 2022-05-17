#!/usr/bin/env python

import json
import logging

import pandas as pd


class Mt5ResponseError(RuntimeError):
    pass


def set_log_config(debug=None, info=None):
    if debug:
        lv = logging.DEBUG
    elif info:
        lv = logging.INFO
    else:
        lv = logging.WARNING
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S', level=lv
    )


def print_json(data, indent=2):
    print(json.dumps(data, indent=indent))


def print_df(df, csv_path=None, display_max_columns=500, display_width=1500):
    logger = logging.getLogger(__name__)
    logger.debug(f'df.shape: {df.shape}')
    logger.debug(f'df.dtypes: {df.dtypes}')
    logger.debug(f'df: {df}')
    pd.set_option('display.max_columns', display_max_columns)
    pd.set_option('display.width', display_width)
    pd.set_option('display.max_rows', df.shape[0])
    print(df.reset_index().to_string(index=False))
    if csv_path:
        logger.info(f'Write CSV data: {csv_path}')
        df.to_csv(csv_path)
