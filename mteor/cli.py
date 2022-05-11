#!/usr/bin/env python
"""
Automated Trader using MetaTrader 5

Usage:
  mteor -h|--help
  mteor --version
  mteor mt5 [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>]
  mteor ohlc [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--granularity=<str>]
    [--count=<int>] <instrument>

Options:
  -h, --help            Print help and exit
  --version             Print version and exit
  --debug, --info       Execute a command with debug|info messages
  --mt5-exe=<path>      Specify a path to a MetaTrader 5 (MT5) exe file
  --mt5-login=<str>     Specify a MT5 trading account number
  --mt5-password=<str>  Specify a MT5 trading account password
  --mt5-server=<str>    Specify a MT5 trade server name
  --granularity=<str>   Specify a timeframe granularity [default: M1]
  --count=<int>         Specify a record count [default: 10]

Arguments:
  <instrument>          Financial instrument symbol
"""

import logging
import os

import MetaTrader5 as Mt5
import pandas as pd
from docopt import docopt

from . import __version__


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    _set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
    _initialize_mt5(args=args)
    if args['mt5']:
        _print_mt5_info()
    elif args['ohlc']:
        _print_ohlc(
            symbol=args['<instrument>'], granularity=args['--granularity'],
            count=int(args['--count'])
        )
    else:
        pass
    Mt5.shutdown()


def _print_ohlc(symbol, granularity, count, start_pos=0,
                display_max_columns=500, display_width=1500):
    pd.set_option('display.max_columns', display_max_columns)
    pd.set_option('display.max_rows', count)
    pd.set_option('display.width', display_width)
    print(
        _fetch_df_rate(
            symbol=symbol, granularity=granularity, count=count,
            start_pos=start_pos
        ).reset_index().to_string(index=False)
    )


def _fetch_df_rate(symbol, granularity, count, start_pos=0):
    return pd.DataFrame(
        Mt5.copy_rates_from_pos(
            symbol, getattr(Mt5, f'TIMEFRAME_{granularity}'), start_pos, count
        )
    ).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s')
    ).set_index('time')


def _print_mt5_info():
    print(f'MetaTrader5 package author:\t{Mt5.__author__}')
    print(f'MetaTrader5 package version:\t{Mt5.__version__}')
    print('Terminal version:\t{}'.format(Mt5.version()))
    print('Terminal status and settings:\t{}'.format(Mt5.terminal_info()))
    print('Trading account info:\t{}'.format(Mt5.account_info()))
    print('Number of financial instruments:\t{}'.format(Mt5.symbols_total()))


def _initialize_mt5(args):
    initialize_kwargs = {
        **({'path': args['--mt5-exe']} if args['--mt5-exe'] else dict()),
        **(
            {'login': int(args['--mt5-login'])}
            if args['--mt5-login'] else dict()
        ),
        **(
            {'password': args['--mt5-password']}
            if args['--mt5-password'] else dict()
        ),
        **(
            {'server': args['--mt5-server']}
            if args['--mt5-server'] else dict()
        )
    }
    if not Mt5.initialize(**initialize_kwargs):
        raise RuntimeError(
            'MetaTrader5.initialize() failed, '
            + 'error code = {}'.format(Mt5.last_error())
        )


def _set_log_config(debug=None, info=None):
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
