#!/usr/bin/env python

import logging
import os
from datetime import datetime, timedelta

import MetaTrader5 as Mt5
import pandas as pd

from .util import print_df, print_json


def print_deals(hours, date_to=None, group=None):
    logger = logging.getLogger(__name__)
    logger.info(f'hours: {hours}, date_to: {date_to}, group: {group}')
    end_date = (pd.to_datetime(date_to) if date_to else datetime.utcnow())
    logger.info(f'end_date: {end_date}')
    deals = Mt5.history_deals_get(
        (end_date - timedelta(hours=float(hours))), end_date,
        **({'group': group} if group else dict())
    )
    logger.debug(f'deals: {deals}')
    print_json([d._asdict() for d in deals])


def print_orders():
    logger = logging.getLogger(__name__)
    orders = Mt5.orders_get()
    logger.debug(f'orders: {orders}')
    print_json([o._asdict() for o in orders])


def print_positions():
    logger = logging.getLogger(__name__)
    positions = Mt5.positions_get()
    logger.debug(f'positions: {positions}')
    print_json([p._asdict() for p in positions])


def print_margins(symbol):
    logger = logging.getLogger(__name__)
    logger.info(f'symbol: {symbol}')
    account_currency = Mt5.account_info().currency
    logger.info(f'account_currency: {account_currency}')
    volume_min = Mt5.symbol_info(symbol).volume_min
    logger.info(f'volume_min: {volume_min}')
    symbol_info_tick = Mt5.symbol_info_tick(symbol)
    logger.debug(f'symbol_info_tick: {symbol_info_tick}')
    ask_margin = Mt5.order_calc_margin(
        Mt5.ORDER_TYPE_BUY, symbol, volume_min, symbol_info_tick.ask
    )
    logger.info(f'ask_margin: {ask_margin}')
    bid_margin = Mt5.order_calc_margin(
        Mt5.ORDER_TYPE_SELL, symbol, volume_min, symbol_info_tick.bid
    )
    logger.info(f'bid_margin: {bid_margin}')
    print_json({
        'symbol': symbol, 'account_currency': account_currency,
        'volume': volume_min, 'margin': {'ask': ask_margin, 'bid': bid_margin}
    })


def print_ticks(symbol, seconds, date_to=None, csv_path=None):
    logger = logging.getLogger(__name__)
    logger.info(
        f'symbol: {symbol}, seconds: {seconds}, date_to: {date_to}'
        + f', csv_path: {csv_path}'
    )
    print_df(
        _fetch_df_tick(symbol=symbol, seconds=seconds, date_to=date_to),
        csv_path=csv_path
    )


def _fetch_df_tick(symbol, seconds, date_to=None):
    logger = logging.getLogger(__name__)
    delta = timedelta(seconds=seconds)
    if date_to:
        end_date = pd.to_datetime(date_to)
        start_date = end_date - delta
    else:
        symbol_info_tick = Mt5.symbol_info_tick(symbol)
        logger.debug(f'symbol_info_tick: {symbol_info_tick}')
        last_tick_time = pd.to_datetime(symbol_info_tick.time, unit='s')
        end_date = last_tick_time + delta
        start_date = last_tick_time - delta
    logger.info(f'start_date: {start_date}, end_date: {end_date}')
    ticks = Mt5.copy_ticks_range(
        symbol, start_date, end_date, Mt5.COPY_TICKS_ALL
    )
    logger.debug(f'ticks: {ticks}')
    return pd.DataFrame(ticks).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s'),
        time_msc=lambda d: pd.to_datetime(d['time_msc'], unit='ms')
    ).set_index(['time', 'time_msc'])


def print_rates(symbol, granularity, count, start_pos=0, csv_path=None):
    logger = logging.getLogger(__name__)
    logger.info(
        f'symbol: {symbol}, granularity: {granularity}, count: {count}'
        + f', start_pos: {start_pos}, csv_path: {csv_path}'
    )
    print_df(
        _fetch_df_rate(
            symbol=symbol, granularity=granularity, count=count,
            start_pos=start_pos
        ),
        csv_path=csv_path
    )


def _fetch_df_rate(symbol, granularity, count, start_pos=0):
    logger = logging.getLogger(__name__)
    timeframe = getattr(Mt5, f'TIMEFRAME_{granularity}')
    logger.info(f'Mt5.TIMEFRAME_{granularity}: {timeframe}')
    rates = Mt5.copy_rates_from_pos(symbol, timeframe, start_pos, int(count))
    logger.debug(f'rates: {rates}')
    return pd.DataFrame(rates).assign(
        time=lambda d: pd.to_datetime(d['time'], unit='s')
    ).set_index('time')


def print_symbol_info(symbol):
    logger = logging.getLogger(__name__)
    logger.info(f'symbol: {symbol}')
    symbol_info = Mt5.symbol_info(symbol)
    logger.debug(f'symbol_info: {symbol_info}')
    symbol_info_tick = Mt5.symbol_info_tick(symbol)
    logger.debug(f'symbol_info_tick: {symbol_info_tick}')
    print_json({
        'symbol': symbol, 'info': symbol_info._asdict(),
        'tick': symbol_info_tick._asdict()
    })


def print_mt5_info():
    logger = logging.getLogger(__name__)
    logger.info(f'Mt5.__version__: {Mt5.__version__}')
    logger.info(f'Mt5.__author__: {Mt5.__author__}')
    terminal_version = Mt5.version()
    logger.debug(f'terminal_version: {terminal_version}')
    print(
        os.linesep.join([
            f'{k}: {v}' for k, v in zip(
                [
                    'MetaTrader 5 terminal version', 'Build',
                    'Build release date'
                ],
                terminal_version
            )
        ])
    )
    terminal_info = Mt5.terminal_info()
    logger.debug(f'terminal_info: {terminal_info}')
    print(
        f'Terminal status and settings:{os.linesep}' + os.linesep.join([
            f'  {k}: {v}' for k, v in terminal_info._asdict().items()
        ])
    )
    account_info = Mt5.account_info()
    logger.debug(f'account_info: {account_info}')
    print(
        f'Trading account info:{os.linesep}' + os.linesep.join([
            f'  {k}: {v}' for k, v in account_info._asdict().items()
        ])
    )
    print('Number of financial instruments: {}'.format(Mt5.symbols_total()))
