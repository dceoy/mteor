#!/usr/bin/env python
"""
Automated Trader using MetaTrader 5

Usage:
  mteor -h|--help
  mteor --version
  mteor mt5 [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>]
  mteor symbol [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] <instrument>
  mteor rate [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--granularity=<str>]
    [--count=<int>] <instrument>
  mteor tick [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--period=<sec>]
    [--date-to=<date>] <instrument>

Commands:
    mt5                 Print MT5 versions, status, and settings
    symbol              Print information about a financial instrument
    rate                Print rates of a financial instrument
    tick                Print ticks of a financial instrument

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
  --period=<sec>        Specify a period of seconds to look back [default: 60]
  --date-to=<date>      Specify an ending datetime

Arguments:
  <instrument>          Financial instrument symbol
"""

import logging
import os
from datetime import datetime, timedelta
from pprint import pformat, pprint

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
    try:
        if args['mt5']:
            _print_mt5_info()
        elif args['symbol']:
            _print_symbol_info(symbol=args['<instrument>'])
        elif args['rate']:
            _print_rate(
                symbol=args['<instrument>'], granularity=args['--granularity'],
                count=int(args['--count'])
            )
        elif args['tick']:
            _print_tick(
                symbol=args['<instrument>'], period=float(args['--period']),
                date_to=args['--date-to']
            )
        else:
            pass
    except Exception as e:
        raise e
    finally:
        Mt5.shutdown()


def _print_symbol_info(symbol, indent=4):
    selected_symbol = Mt5.symbol_select(symbol, True)
    if not selected_symbol:
        raise RuntimeError(f'Failed to select: {symbol}')
    else:
        pprint(Mt5.symbol_info(symbol)._asdict())


def _print_tick(symbol, period, date_to=None):
    _print_df(_fetch_df_tick(symbol=symbol, period=period, date_to=date_to))


def _fetch_df_tick(symbol, period, date_to=None):
    end_date = (pd.to_datetime(date_to) if date_to else datetime.now())
    return pd.DataFrame(
        Mt5.copy_ticks_range(
            symbol, (end_date - timedelta(seconds=period)), end_date,
            Mt5.COPY_TICKS_ALL
        )
    ).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s')
    ).set_index('time')


def _print_df(df, display_max_columns=500, display_width=1500):
    pd.set_option('display.max_columns', display_max_columns)
    pd.set_option('display.width', display_width)
    pd.set_option('display.max_rows', df.shape[0])
    print(df.reset_index().to_string(index=False))


def _print_rate(symbol, granularity, count, start_pos=0):
    _print_df(
        _fetch_df_rate(
            symbol=symbol, granularity=granularity, count=count,
            start_pos=start_pos
        )
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
    print(
        'Terminal status and settings:' + os.linesep
        + pformat(Mt5.terminal_info()._asdict())
    )
    print(
        'Trading account info:' + os.linesep
        + pformat(Mt5.account_info()._asdict())
    )
    print('Number of financial instruments:\t{}'.format(Mt5.symbols_total()))
    print('Number of active orders:\t{}'.format(Mt5.orders_total()))
    print('Number of open positions:\t{}'.format(Mt5.positions_total()))


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
