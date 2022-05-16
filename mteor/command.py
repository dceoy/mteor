#!/usr/bin/env python

import logging
import os
from datetime import datetime, timedelta
from pprint import pformat, pprint

import MetaTrader5 as Mt5
import pandas as pd


def close_positions(symbol, dry_run=False):
    logger = logging.getLogger(__name__)
    for p in Mt5.positions_get(symbol=symbol):
        request = {
            'action': Mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': p.volume,
            'type': Mt5.ORDER_TYPE_CLOSE_BY,
            'type_filling': Mt5.ORDER_FILLING_FOK,
            'type_time': Mt5.ORDER_TIME_GTC,
            'position': p.identifier
        }
        order_check_result = Mt5.order_check(request)
        logger.info(
            'order_check_result:' + os.linesep
            + pformat({
                k: (v._asdict() if k == 'request' else v)
                for k, v in order_check_result._asdict().items()
            })
        )
        if dry_run:
            order_send_result = Mt5.order_send(request)
            logger.info(
                'order_send_result:' + os.linesep
                + pformat({
                    k: (v._asdict() if k == 'request' else v)
                    for k, v in order_send_result._asdict().items()
                })
            )


def print_deals(hours, date_to=None, group=None):
    end_date = (
        pd.to_datetime(date_to) if date_to
        else (datetime.now() + timedelta(seconds=1))
    )
    pprint([
        p._asdict() for p in Mt5.history_deals_get(
            (end_date - timedelta(hours=float(hours))), end_date,
            **({'group': group} if group else dict())
        )
    ])


def print_orders():
    pprint([p._asdict() for p in Mt5.orders_get()])


def print_positions():
    pprint([p._asdict() for p in Mt5.positions_get()])


def print_margins(symbol):
    volume_min = Mt5.symbol_info(symbol).volume_min
    symbol_info_tick = Mt5.symbol_info_tick(symbol)
    pprint({
        'symbol': symbol,
        'account_currency': Mt5.account_info().currency,
        'volume': volume_min,
        'margin': {
            'ask': Mt5.order_calc_margin(
                Mt5.ORDER_TYPE_BUY, symbol, volume_min, symbol_info_tick.ask
            ),
            'bid': Mt5.order_calc_margin(
                Mt5.ORDER_TYPE_SELL, symbol, volume_min, symbol_info_tick.bid
            )
        }
    })


def print_ticks(symbol, seconds, date_to=None, csv_path=None):
    _print_df(
        _fetch_df_tick(symbol=symbol, seconds=seconds, date_to=date_to),
        csv_path=csv_path
    )


def _fetch_df_tick(symbol, seconds, date_to=None):
    end_date = (
        pd.to_datetime(date_to) if date_to
        else (datetime.now() + timedelta(seconds=1))
    )
    return pd.DataFrame(
        Mt5.copy_ticks_range(
            symbol, (end_date - timedelta(seconds=float(seconds))), end_date,
            Mt5.COPY_TICKS_ALL
        )
    ).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s')
    ).set_index('time')


def _print_df(df, csv_path=None, display_max_columns=500, display_width=1500):
    pd.set_option('display.max_columns', display_max_columns)
    pd.set_option('display.width', display_width)
    pd.set_option('display.max_rows', df.shape[0])
    print(df.reset_index().to_string(index=False))
    if csv_path:
        df.to_csv(csv_path)


def print_rates(symbol, granularity, count, start_pos=0, csv_path=None):
    _print_df(
        _fetch_df_rate(
            symbol=symbol, granularity=granularity, count=count,
            start_pos=start_pos
        ),
        csv_path=csv_path
    )


def _fetch_df_rate(symbol, granularity, count, start_pos=0):
    return pd.DataFrame(
        Mt5.copy_rates_from_pos(
            symbol, getattr(Mt5, f'TIMEFRAME_{granularity}'), start_pos,
            int(count)
        )
    ).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s')
    ).set_index('time')


def print_symbol_info(symbol, indent=4):
    selected_symbol = Mt5.symbol_select(symbol, True)
    if not selected_symbol:
        raise RuntimeError(f'Failed to select: {symbol}')
    else:
        pprint({'symbol': symbol, 'info': Mt5.symbol_info(symbol)._asdict()})


def print_mt5_info():
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
