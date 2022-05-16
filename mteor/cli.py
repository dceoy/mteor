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
    [--mt5-password=<str>] [--mt5-server=<str>] [--csv=<path>]
    [--granularity=<str>] [--count=<int>] <instrument>
  mteor tick [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--csv=<path>]
    [--seconds=<float>] [--date-to=<date>] <instrument>
  mteor margin [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] <instrument>
  mteor position [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>]
  mteor order [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>]
  mteor deal [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--hours=<floatt>]
    [--date-to=<date>]
  mteor close [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
    [--mt5-password=<str>] [--mt5-server=<str>] [--dry-run] <instrument>

Commands:
    mt5                   Print MT5 versions, status, and settings
    symbol                Print information about a financial instrument
    rate                  Print rates of a financial instrument
    tick                  Print ticks of a financial instrument
    margin                Print minimum margins to perform trading operations
    position              Print open positions
    order                 Print active orders
    deal                  Print deals from trading history
    close                 Close open positions

Options:
    -h, --help            Print help and exit
    --version             Print version and exit
    --debug, --info       Execute a command with debug|info messages
    --mt5-exe=<path>      Specify a path to a MetaTrader 5 (MT5) exe file
    --mt5-login=<str>     Specify a MT5 trading account number
    --mt5-password=<str>  Specify a MT5 trading account password
    --mt5-server=<str>    Specify a MT5 trade server name
    --csv=<path>          Write data with CSV into a file
    --granularity=<str>   Specify a timeframe granularity [default: M1]
    --count=<int>         Specify a record count [default: 10]
    --seconds=<float>     Specify seconds to look back [default: 60]
    --date-to=<date>      Specify an ending datetime
    --hours=<float>       Specify hours to look back [default: 24]
    --dry-run             Invoke a command with dry-run mode

Arguments:
    <instrument>          Financial instrument symbol
"""

import logging
import os

import MetaTrader5 as Mt5
from docopt import docopt

from . import __version__
from .command import (close_positions, print_deals, print_margins,
                      print_mt5_info, print_orders, print_positions,
                      print_rates, print_symbol_info, print_ticks)


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    _set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
    try:
        _initialize_mt5(args=args)
        if args['mt5']:
            print_mt5_info()
        elif args['symbol']:
            print_symbol_info(symbol=args['<instrument>'])
        elif args['rate']:
            print_rates(
                symbol=args['<instrument>'], granularity=args['--granularity'],
                count=args['--count'], csv_path=args['--csv']
            )
        elif args['tick']:
            print_ticks(
                symbol=args['<instrument>'], seconds=args['--seconds'],
                date_to=args['--date-to'], csv_path=args['--csv']
            )
        elif args['margin']:
            print_margins(symbol=args['<instrument>'])
        elif args['position']:
            print_positions()
        elif args['order']:
            print_orders()
        elif args['deal']:
            print_deals(hours=args['--hours'], date_to=args['--date-to'])
        elif args['close']:
            close_positions(
                symbol=args['<instrument>'], dry_run=args['--dry-run']
            )
        else:
            pass
    except Exception as e:
        logger.error('the last error of MetaTrader5:', Mt5.last_error())
        raise e
    finally:
        Mt5.shutdown()


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
        raise RuntimeError('MetaTrader5.initialize() failed.')


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
