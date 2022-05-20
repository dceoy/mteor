#!/usr/bin/env python

import logging
import os
from datetime import datetime, timedelta
from math import ceil
from pprint import pformat

import MetaTrader5 as Mt5
import numpy as np
import pandas as pd

from .bet import BettingSystem
from .util import Mt5ResponseError


class Mt5TraderCore(object):
    def __init__(self, symbol, betting_strategy='constant',
                 scanned_history_hours=24, scanned_tick_seconds=60,
                 hv_granularity='M1', hv_count=1000, unit_margin_ratio=0.01,
                 preserved_margin_ratio=0.01, take_profit_limit_ratio=0.01,
                 trailing_stop_limit_ratio=0.01, stop_loss_limit_ratio=0.01,
                 quiet=False, dry_run=False):
        self.__logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.betting_system = BettingSystem(strategy=betting_strategy)
        self.__scanned_history_hours = float(scanned_history_hours)
        self.__scanned_tick_seconds = float(scanned_tick_seconds)
        self.__hv_granularity = hv_granularity
        self.__hv_count = int(hv_count)
        self.__unit_margin_ratio = float(unit_margin_ratio)
        self.__preserved_margin_ratio = float(preserved_margin_ratio)
        self.__take_profit_limit_ratio = float(take_profit_limit_ratio)
        self.__trailing_stop_limit_ratio = float(trailing_stop_limit_ratio)
        self.__stop_loss_limit_ratio = float(stop_loss_limit_ratio)
        self.__quiet = quiet
        self.__dry_run = dry_run
        self.account_info = None
        self.symbol_info = None
        self.symbol_info_tick = None
        self.positions = list()
        self.orders = list()
        self.min_margins = dict()
        self.history_deals = list()
        self.df_tick = pd.DataFrame()
        self.df_rate = pd.DataFrame()
        self.unit_margin = None
        self.unit_volume = None
        self.avail_margin = None
        self.avail_volume = None

    def _refresh_account_cache(self):
        self.account_info = Mt5.account_info()
        self.__logger.debug(f'self.account_info: {self.account_info}')
        if not self.account_info:
            raise Mt5ResponseError('Mt5.account_info() failed.')

    def _refresh_symbol_cache(self):
        self.symbol_info = Mt5.symbol_info(self.symbol)
        self.__logger.debug(f'self.symbol_info: {self.symbol_info}')
        self.symbol_info_tick = Mt5.symbol_info_tick(self.symbol)
        self.__logger.debug(f'self.symbol_info_tick: {self.symbol_info_tick}')
        for a in ['symbol_info', 'symbol_info_tick']:
            if not getattr(self, a):
                raise Mt5ResponseError(f'Mt5.{a}() failed.')

    def _refresh_position_cache(self):
        self.positions = Mt5.positions_get(symbol=self.symbol)
        self.__logger.debug(f'self.positions: {self.positions}')
        if not isinstance(self.positions, tuple):
            raise Mt5ResponseError('Mt5.positions_get() failed.')

    def _refresh_order_cache(self):
        self.orders = Mt5.orders_get(symbol=self.symbol)
        self.__logger.debug(f'self.orders: {self.orders}')
        if not isinstance(self.orders, tuple):
            raise Mt5ResponseError('Mt5.orders_get() failed.')

    def _refresh_margin_cache(self):
        min_ask_margin = Mt5.order_calc_margin(
            Mt5.ORDER_TYPE_BUY, self.symbol, self.symbol_info.volume_min,
            self.symbol_info_tick.ask
        )
        self.__logger.debug(f'min_ask_margin: {min_ask_margin}')
        min_bid_margin = Mt5.order_calc_margin(
            Mt5.ORDER_TYPE_SELL, self.symbol, self.symbol_info.volume_min,
            self.symbol_info_tick.bid
        )
        self.__logger.debug(f'min_bid_margin: {min_bid_margin}')
        if all([min_ask_margin, min_bid_margin]):
            self.min_margins = {
                'ask': min_ask_margin, 'bid': min_bid_margin,
                'mid': ((min_ask_margin + min_bid_margin) / 2)
            }
        else:
            raise Mt5ResponseError('Mt5.order_calc_margin() failed.')

    def _refresh_history_deal_cache(self):
        end_date = datetime.now() + timedelta(seconds=1)
        self.history_deals = Mt5.history_deals_get(
            (end_date - timedelta(hours=self.__scanned_history_hours)),
            end_date, group=self.symbol
        )
        if not isinstance(self.history_deals, tuple):
            raise Mt5ResponseError('Mt5.history_deals_get() failed.')

    def _fetch_df_tick(self):
        end_date = datetime.now() + timedelta(seconds=1)
        start_date = end_date - timedelta(seconds=self.__scanned_tick_seconds)
        ticks = Mt5.copy_ticks_range(
            self.symbol, start_date, end_date, Mt5.COPY_TICKS_ALL
        )
        self.__logger.debug(f'ticks: {ticks}')
        if isinstance(ticks, list):
            self.df_tick = pd.DataFrame(ticks)[[
                'time_msc', 'bid', 'ask'
            ]].assign(
                time_msc=lambda d: pd.to_datetime(d['time_msc'], unit='ms')
            ).set_index('time_msc')
        else:
            raise Mt5ResponseError('Mt5.copy_ticks_range() failed.')

    def _fetch_df_rate(self):
        rates = Mt5.copy_rates_from_pos(
            self.symbol, getattr(Mt5, f'TIMEFRAME_{self.__hv_granularity}'), 0,
            self.__hv_count
        )
        self.__logger.debug(f'rates: {rates}')
        if isinstance(rates, list):
            self.df_rate = pd.DataFrame(rates).drop(
                columns='real_volume'
            ).assign(
                time=lambda d: pd.to_datetime(d['time'], unit='s')
            ).set_index('time')
        else:
            raise Mt5ResponseError('Mt5.copy_rates_from_pos() failed.')

    def _send_or_check_order(self, request):
        self.__logger.debug(f'request: {request}')
        order_func = 'order_{}'.format('check' if self.__dry_run else 'send')
        result = getattr(Mt5, order_func)(request)
        self.__logger.debug(f'result: {result}')
        response = {
            k: (v._asdict() if k == 'request' else v)
            for k, v in result._asdict().items()
        }
        if (((not self.__dry_run) and result.retcode == Mt5.TRADE_RETCODE_DONE)
                or (self.__dry_run and result.retcode == 0)):
            self.__logger.info(f'response:{os.linesep}' + pformat(response))
        else:
            self.__logger.error(f'response:{os.linesep}' + pformat(response))
            raise Mt5ResponseError(
                f'Mt5.{order_func}() failed. <= `{result.comment}`'
            )

    def _close_positions(self, **kwargs):
        if not self.positions:
            self.__logger.info(f'No position for {self.symbol}.')
        else:
            for p in self.positions:
                self._send_or_check_order({
                    'action': Mt5.TRADE_ACTION_DEAL,
                    'symbol': p.symbol, 'volume': p.volume,
                    'type': (
                        Mt5.ORDER_TYPE_SELL
                        if p.type == Mt5.POSITION_TYPE_BUY
                        else Mt5.ORDER_TYPE_BUY
                    ),
                    'type_filling': Mt5.ORDER_FILLING_RETURN,
                    'type_time': Mt5.ORDER_TIME_GTC,
                    'position': p.ticket, **kwargs
                })

    def _refresh_unit_margin_and_volume(self):
        unit_lot = ceil(
            self.account_info.balance * self.__unit_margin_ratio
            / self.min_margins['ask']
        )
        self.unit_margin = self.min_margins['ask'] * unit_lot
        self.__logger.debug(f'self.unit_margin: {self.unit_margin}')
        self.unit_volume = self.symbol_info.volume_min * unit_lot
        self.__logger.debug(f'self.unit_volume: {self.unit_volume}')
        self.avail_margin = max(
            (
                self.account_info.margin_free
                - self.account_info.balance * self.__preserved_margin_ratio
            ),
            0
        )
        self.__logger.debug(f'self.avail_margin: {self.avail_margin}')
        self.avail_volume = (
            ceil(self.avail_margin / self.min_margins['ask'])
            * self.symbol_info.volume_min
        )
        self.__logger.debug(f'self.avail_volume: {self.avail_volume}')

    def _determine_order_volume(self):
        bet_volume = self.betting_system.calculate_volume_by_pl(
            unit_volume=self.unit_volume, history_deals=self.history_deals
        )
        self.__logger.debug(f'bet_volume: {bet_volume}')
        return min(bet_volume, self.avail_volume)

    def _determine_order_limits(self, side):
        price = getattr(
            self.symbol_info_tick, {'long': 'ask', 'short': 'bid'}[side]
        )
        order_limits = {
            'sl': (
                price + (
                    price * self.__stop_loss_limit_ratio
                    * {'long': -1, 'short': 1}[side]
                )
            ),
            'tp': (
                price + (
                    price * self.__take_profit_limit_ratio
                    * {'long': 1, 'short': -1}[side]
                )
            )
        }
        self.__logger.debug(f'order_limits: {order_limits}')
        return order_limits

    def _place_order(self, volume, side, **kwargs):
        self._send_or_check_order({
            'action': Mt5.TRADE_ACTION_DEAL,
            'symbol': self.symbol, 'volume': volume,
            'type':
            {'long': Mt5.ORDER_TYPE_BUY, 'short': Mt5.ORDER_TYPE_SELL}[side],
            'type_filling': Mt5.ORDER_FILLING_FOK,
            'type_time': Mt5.ORDER_TIME_GTC,
            **kwargs
        })

    def design_and_place_order(self, act):
        position_volumes = {
            'long': sum([
                p.volume for p in self.positions
                if p.type == Mt5.POSITION_TYPE_BUY
            ]),
            'short': sum([
                p.volume for p in self.positions
                if p.type == Mt5.POSITION_TYPE_SELL
            ])
        }
        if position_volumes['long'] > position_volumes['short']:
            position_side = 'long'
        elif position_volumes['long'] < position_volumes['short']:
            position_side = 'short'
        else:
            position_side = None
        if (position_side and act
                and (act == 'closing' or act != position_side)):
            self.__logger.info('Close a position: {}'.format(position_side))
            self._close_positions()
        if act in ['long', 'short']:
            order_limits = self._determine_order_limits(side=act)
            order_volume = self._determine_order_volume()
            new_volume = (
                order_volume - position_volumes[act]
                if position_side and act == position_side else order_volume
            )
            if new_volume > 0:
                self.__logger.info(f'Open an order: {act}')
                self._place_order(volume=new_volume, side=act, **order_limits)
            else:
                self.__logger.info(f'Skip an order: {act}')
            return new_volume
        else:
            return 0

    def is_margin_lack(self):
        return (
            (not self.position) and (
                self.unit_margin >= self.account_info.margin_free
                or self.unit_volume == 0
                or (
                    self.account_info.balance * self.__preserved_margin_ratio
                    >= self.account_info.margin_free
                )
            )
        )

    def print_log(self, data):
        self.__logger.debug(f'console log: {data}')
        if not self.__quiet:
            print(data, flush=True)

    def print_state_line(self, add_str):
        self.print_log(
            '|{0:^11}|{1:^29}|'.format(
                self.symbol,
                'B/A:{:>21}'.format(
                    np.array2string(
                        np.array([
                            self.symbol_info_tick.bid,
                            self.symbol_info_tick.ask
                        ]),
                        formatter={'float_kind': lambda f: f'{f:8g}'}
                    )
                )
            ) + (add_str or '')
        )
