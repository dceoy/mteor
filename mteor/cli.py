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
        [--seconds=<float>] [--date-to=<date>] [--thin] <instrument>
    mteor margin [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>] <instrument>
    mteor position [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>]
    mteor order [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>]
    mteor deal [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>] [--hours=<float>]
        [--date-to=<date>]
    mteor close [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>] [--dry-run]
        <instrument>...
    mteor open [--debug|--info] [--mt5-exe=<path>] [--mt5-login=<str>]
        [--mt5-password=<str>] [--mt5-server=<str>] [--betting-strategy=<str>]
        [--history-hours=<float>] [--unit-volume=<float>|--unit-margin=<ratio>]
        [--preserved-margin=<ratio>] [--take-profit-limit=<float>]
        [--stop-loss-limit=<float>] [--trailing-stop-limit=<float>]
        [--hv-granularity=<str>] [--hv-count=<int>] [--hv-ema-span=<int>]
        [--max-spread=<float>] [--sleeping=<ratio>] [--lrr-ema-span=<int>]
        [--sr-ema-span=<int>] [--significance-level=<float>]
        [--interval-seconds=<float>] [--retry-count=<int>] [--quiet]
        [--dry-run] <instrument>...

Commands:
    mt5                 Print MetaTrader 5 versions, status, and settings
    symbol              Print information about a financial instrument
    rate                Print rates of a financial instrument
    tick                Print ticks of a financial instrument
    margin              Print minimum margins to perform trading operations
    position            Print open positions
    order               Print active orders
    deal                Print deals from trading history
    close               Close open positions
    open                Invoke an autonomous trader

Options:
    -h, --help          Print help and exit
    --version           Print version and exit
    --debug, --info     Execute a command with debug|info messages
    --mt5-exe=<path>    Specify a path to a MetaTrader 5 (MT5) exe file
    --mt5-login=<str>   Specify a MT5 trading account number
    --mt5-password=<str>
                        Specify a MT5 trading account password
    --mt5-server=<str>  Specify a MT5 trade server name
    --csv=<path>        Write data with CSV into a file
    --granularity=<str>
                        Specify a timeframe granularity [default: M1]
    --count=<int>       Specify a record count [default: 10]
    --seconds=<float>   Specify seconds to look back [default: 60]
    --date-to=<date>    Specify an ending datetime
    --thin              Thin ticks by timestamp
    --hours=<float>     Specify hours to look back [default: 24]
    --dry-run           Invoke a command with dry-run mode
    --betting-strategy=<str>
                        Specify the betting strategy [default: constant]
                        {constant, martingale, paroli, dalembert, oscarsgrind}
    --history-hours=<float>
                        Specify hours for deal history [default: 24]
    --unit-volume=<float>
                        Specify the unit volume to NAV [default: 1]
    --unit-margin=<ratio>
                        Specify the unit margin ratio to NAV
                        (This overrides --unit-volume)
    --preserved-margin=<ratio>
                        Specify the preserved margin ratio [default: 0.01]
    --take-profit-limit=<float>
                        Specify the take-profit limit ratio [default: 0.01]
    --trailing-stop-limit=<float>
                        Specify the trailing-stop limit ratio [default: 0.01]
    --stop-loss-limit=<float>
                        Specify the stop-loss limit ratio [default: 0.01]
    --hv-granularity=<str>
                        Specify the granularity for HV [default: M1]
    --hv-count=<int>    Specify the count for HV [default: 86400]
    --hv-ema-span=<int>
                        Specify the EMA span for HV [default: 60]
    --max-spread=<float>
                        Specify the max spread ratio [default: 0.01]
    --sleeping=<ratio>  Specify the daily sleeping ratio [default: 0]
    --lrr-ema-span=<int>
                        Specify the EMA span for LRR signal [default: 1000]
    --sr-ema-span=<int>
                        Specify the EMA span for SR signal [default: 1000]
    --significance-level=<float>
                        Specify the significance level [default: 0.01]
    --interval-seconds=<float>
                        Wait seconds between iterations [default: 0]
    --retry-count=<int>
                        Set the retry count due to API errors [default: 1]

Arguments:
    <instrument>        Financial instrument symbol
"""

import logging
import os

import MetaTrader5 as Mt5
from docopt import docopt

from . import __version__
from .info import (print_deals, print_margins, print_mt5_info, print_orders,
                   print_positions, print_rates, print_symbol_info,
                   print_ticks)
from .order import close_positions
from .trader import AutoTrader
from .util import Mt5ResponseError, set_log_config


def main():
    args = docopt(__doc__, version=f'mteor {__version__}')
    set_log_config(debug=args['--debug'], info=args['--info'])
    logger = logging.getLogger(__name__)
    logger.debug(f'args:{os.linesep}{args}')
    try:
        _initialize_mt5(args=args)
        if args.get('open'):
            logger.info('Autonomous trading')
            AutoTrader(
                symbols=args['<instrument>'],
                betting_strategy=args['--betting-strategy'],
                history_hours=args['--history-hours'],
                unit_volume=args['--unit-volume'],
                unit_margin_ratio=args['--unit-margin'],
                preserved_margin_ratio=args['--preserved-margin'],
                take_profit_limit_ratio=args['--take-profit-limit'],
                stop_loss_limit_ratio=args['--stop-loss-limit'],
                trailing_stop_limit_ratio=args['--trailing-stop-limit'],
                hv_granularity=args['--hv-granularity'],
                hv_count=args['--hv-count'], hv_ema_span=args['--hv-ema-span'],
                max_spread_ratio=args['--max-spread'],
                sleeping_ratio=args['--sleeping'],
                lrr_ema_span=args['--lrr-ema-span'],
                sr_ema_span=args['--sr-ema-span'],
                significance_level=args['--significance-level'],
                interval_seconds=args['--interval-seconds'],
                retry_count=args['--retry-count'], quiet=args['--quiet'],
                dry_run=args['--dry-run']
            ).invoke()
        elif args['mt5']:
            print_mt5_info()
        elif args['symbol']:
            print_symbol_info(symbol=args['<instrument>'][0])
        elif args['rate']:
            print_rates(
                symbol=args['<instrument>'][0],
                granularity=args['--granularity'], count=args['--count'],
                csv_path=args['--csv']
            )
        elif args['tick']:
            print_ticks(
                symbol=args['<instrument>'][0], seconds=args['--seconds'],
                date_to=args['--date-to'], csv_path=args['--csv'],
                thin=args['--thin']
            )
        elif args['margin']:
            print_margins(symbol=args['<instrument>'][0])
        elif args['position']:
            print_positions()
        elif args['order']:
            print_orders()
        elif args['deal']:
            print_deals(hours=args['--hours'], date_to=args['--date-to'])
        elif args['close']:
            close_positions(
                symbols=args['<instrument>'], dry_run=args['--dry-run']
            )
        else:
            pass
    except Exception as e:
        logger.error('Mt5.last_error(): {}'.format(Mt5.last_error()))
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
        raise Mt5ResponseError('MetaTrader5.initialize() failed.')
