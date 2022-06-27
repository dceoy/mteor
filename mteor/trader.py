#!/usr/bin/env python

import logging
import os
import signal
import time
from datetime import timedelta
from math import floor
from pprint import pformat

import MetaTrader5 as Mt5
import numpy as np
import pandas as pd
import scipy.stats as scs

from .bet import BettingSystem
from .signal import SignalDetector
from .util import Mt5ResponseError


class Mt5TraderCore(object):
    def __init__(self, symbol, betting_strategy='constant', history_hours=24,
                 unit_volume=1, unit_margin_ratio=None,
                 preserved_margin_ratio=0.01, take_profit_limit_ratio=0.01,
                 stop_loss_limit_ratio=0.01, trailing_stop_limit_ratio=0.01,
                 quiet=False, dry_run=False):
        self.__logger = logging.getLogger(__name__)
        self.symbol = symbol
        self.betting_system = BettingSystem(strategy=betting_strategy)
        self.__history_hours = float(history_hours)
        if unit_margin_ratio:
            self.__unit_margin_ratio = float(unit_margin_ratio)
            self.unit_volume = None
        else:
            self.__unit_margin_ratio = None
            self.unit_volume = float(unit_volume)
        self.__preserved_margin_ratio = float(preserved_margin_ratio)
        self.__take_profit_limit_ratio = float(take_profit_limit_ratio)
        self.__stop_loss_limit_ratio = float(stop_loss_limit_ratio)
        self.__trailing_stop_limit_ratio = float(trailing_stop_limit_ratio)
        self.__quiet = quiet
        self.__dry_run = dry_run
        self.account_info = None
        self.symbol_info = None
        self.symbol_info_tick = None
        self.positions = list()
        self.orders = list()
        self.min_margins = dict()
        self.history_deals = list()
        self.last_tick_time = None
        self.unit_margin = None
        self.avail_margin = None
        self.avail_volume = None
        self.position_volumes = dict()
        self.position_side = None

    def refresh_mt5_caches(self):
        self._refresh_account_info_cache()
        self._refresh_symbol_info_cache()
        self._refresh_symbol_info_tick_cache()
        self._refresh_position_cache()
        self._refresh_order_cache()
        self._refresh_margin_cache()
        self._refresh_history_deal_cache()
        self._refresh_unit_margin_and_volume()

    def _refresh_account_info_cache(self):
        self.account_info = Mt5.account_info()
        self.__logger.debug(f'self.account_info: {self.account_info}')
        if not self.account_info:
            raise Mt5ResponseError('Mt5.account_info() failed.')

    def _refresh_symbol_info_cache(self):
        self.symbol_info = Mt5.symbol_info(self.symbol)
        self.__logger.debug(f'self.symbol_info: {self.symbol_info}')
        if not self.symbol_info:
            raise Mt5ResponseError('Mt5.symbol_info() failed.')

    def _refresh_symbol_info_tick_cache(self):
        self.symbol_info_tick = Mt5.symbol_info_tick(self.symbol)
        self.__logger.debug(f'self.symbol_info_tick: {self.symbol_info_tick}')
        if not self.symbol_info_tick:
            raise Mt5ResponseError('Mt5.symbol_info_tick() failed.')
        else:
            self.last_tick_time = pd.to_datetime(
                self.symbol_info_tick.time, unit='s'
            )
            self.__logger.debug(f'self.last_tick_time: {self.last_tick_time}')

    def _refresh_position_cache(self):
        self.positions = Mt5.positions_get(symbol=self.symbol)
        self.__logger.debug(f'self.positions: {self.positions}')
        if not isinstance(self.positions, tuple):
            raise Mt5ResponseError('Mt5.positions_get() failed.')
        elif not self.positions:
            self.position_volumes = {'long': 0, 'short': 0}
            self.position_side = None
        else:
            long_volume = sum([
                p.volume for p in self.positions
                if p.type == Mt5.POSITION_TYPE_BUY
            ])
            short_volume = sum([
                p.volume for p in self.positions
                if p.type == Mt5.POSITION_TYPE_SELL
            ])
            self.position_volumes = {
                'long': long_volume, 'short': short_volume
            }
            if long_volume > short_volume:
                self.position_side = 'long'
            elif long_volume < short_volume:
                self.position_side = 'short'
            else:
                self.position_side = None

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
            self.min_margins = {'ask': min_ask_margin, 'bid': min_bid_margin}
        else:
            raise Mt5ResponseError('Mt5.order_calc_margin() failed.')

    def _refresh_history_deal_cache(self):
        date_from = (
            self.last_tick_time - timedelta(hours=self.__history_hours)
        )
        date_to = self.last_tick_time + timedelta(hours=self.__history_hours)
        self.history_deals = Mt5.history_deals_get(
            date_from, date_to, group=self.symbol
        )
        if not isinstance(self.history_deals, tuple):
            raise Mt5ResponseError('Mt5.history_deals_get() failed.')

    def _refresh_unit_margin_and_volume(self):
        if self.__unit_margin_ratio:
            unit_lot = floor(
                self.account_info.equity * self.__unit_margin_ratio
                / self.min_margins['ask']
            )
            self.unit_volume = self.symbol_info.volume_min * unit_lot
        else:
            unit_lot = floor(self.unit_volume / self.symbol_info.volume_min)
        self.__logger.debug(f'self.unit_volume: {self.unit_volume}')
        self.unit_margin = self.min_margins['ask'] * unit_lot
        self.__logger.debug(f'self.unit_margin: {self.unit_margin}')
        self.avail_margin = max(
            (
                self.account_info.margin_free
                - self.account_info.equity * self.__preserved_margin_ratio
            ),
            0
        )
        self.__logger.debug(f'self.avail_margin: {self.avail_margin}')
        self.avail_volume = (
            floor(self.avail_margin / self.min_margins['ask'])
            * self.symbol_info.volume_min
        )
        self.__logger.debug(f'self.avail_volume: {self.avail_volume}')

    def trail_and_update_stop_loss(self, **kwargs):
        self._refresh_position_cache()
        if not self.positions:
            self.__logger.info(f'No position for {self.symbol}.')
        else:
            self._refresh_symbol_info_tick_cache()
            for p in self.positions:
                if p.type == Mt5.POSITION_TYPE_SELL:
                    new_sl = round(
                        (
                            self.symbol_info_tick.bid
                            * (1 + self.__trailing_stop_limit_ratio)
                        ),
                        self.symbol_info.digits
                    )
                    trailing_sl = (new_sl if new_sl < p.sl or p.sl == 0 else 0)
                else:
                    new_sl = round(
                        (
                            self.symbol_info_tick.ask
                            * (1 - self.__trailing_stop_limit_ratio)
                        ),
                        self.symbol_info.digits
                    )
                    trailing_sl = (new_sl if new_sl > p.sl or p.sl == 0 else 0)
                if trailing_sl != 0:
                    self._send_or_check_order({
                        'action': Mt5.TRADE_ACTION_SLTP, 'symbol': p.symbol,
                        'sl': trailing_sl, 'tp': p.tp, 'position': p.ticket,
                        **kwargs
                    })

    def close_positions(self, **kwargs):
        self._refresh_position_cache()
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
                    'type_filling': Mt5.ORDER_FILLING_FOK,
                    'type_time': Mt5.ORDER_TIME_GTC,
                    'position': p.ticket, **kwargs
                })

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
            self.__logger.info('response:' + os.linesep + pformat(response))
        else:
            self.__logger.error('response:' + os.linesep + pformat(response))
            raise Mt5ResponseError(
                f'Mt5.{order_func}() failed. <= `{result.comment}`'
            )

    def design_and_place_order(self, act):
        if (self.position_side and act
                and (act == 'closing' or act != self.position_side)):
            self.__logger.info(f'Close a position: {self.position_side}')
            self.close_positions()
        elif self.position_side:
            self.__logger.info(
                f'Update a position stop loss: {self.position_side}'
            )
            self.trail_and_update_stop_loss()
        if act in ['long', 'short']:
            order_limits = self._determine_order_limits(side=act)
            order_volume = self._determine_order_volume()
            new_volume = (
                order_volume - self.position_volumes[act]
                if self.position_side and act == self.position_side
                else order_volume
            )
            if new_volume > 0:
                self.__logger.info(f'Open an order: {act}')
                self._place_order(volume=new_volume, side=act, **order_limits)
                return new_volume
            else:
                self.__logger.info(f'Skip an order: {act}')
                return 0
        else:
            return 0

    def _determine_order_limits(self, side):
        self._refresh_symbol_info_tick_cache()
        if side == 'long':
            sl = self.symbol_info_tick.ask * (1 - self.__stop_loss_limit_ratio)
            tp = (
                self.symbol_info_tick.ask
                * (1 + self.__take_profit_limit_ratio)
            )
        elif side == 'short':
            sl = self.symbol_info_tick.bid * (1 + self.__stop_loss_limit_ratio)
            tp = (
                self.symbol_info_tick.bid
                * (1 - self.__take_profit_limit_ratio)
            )
        else:
            sl = None
            tp = None
        order_limits = {'sl': sl, 'tp': tp}
        self.__logger.debug(f'order_limits: {order_limits}')
        return order_limits

    def _determine_order_volume(self):
        bet_volume = self.betting_system.calculate_volume_by_pl(
            unit_volume=self.unit_volume, history_deals=self.history_deals
        )
        self.__logger.debug(f'bet_volume: {bet_volume}')
        return min(bet_volume, self.avail_volume)

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

    def print_log(self, data):
        self.__logger.debug(f'console log: {data}')
        if not self.__quiet:
            print(data, flush=True)

    def is_margin_lack(self):
        self._refresh_account_info_cache()
        self._refresh_unit_margin_and_volume()
        self._refresh_position_cache()
        return (
            (not self.positions) and (
                self.unit_margin >= self.account_info.margin_free
                or self.unit_volume == 0
                or (
                    self.account_info.equity * self.__preserved_margin_ratio
                    >= self.account_info.margin_free
                )
            )
        )

    def fetch_df_tick(self, tick_seconds=60, thin=True):
        self._refresh_symbol_info_tick_cache()
        date_from = self.last_tick_time - timedelta(seconds=tick_seconds)
        date_to = self.last_tick_time + timedelta(seconds=tick_seconds)
        ticks = Mt5.copy_ticks_range(
            self.symbol, date_from, date_to, Mt5.COPY_TICKS_ALL
        )
        self.__logger.debug(f'ticks: {ticks}')
        if not isinstance(ticks, np.ndarray):
            raise Mt5ResponseError('Mt5.copy_ticks_range() failed.')
        else:
            df_raw_tick = pd.DataFrame(ticks)
            df_tick = (
                self._thin_df_tick(
                    df_tick=df_raw_tick[['time', 'bid', 'ask']].assign(
                        time=lambda d: pd.to_datetime(d['time'], unit='s')
                    )
                ) if thin else df_raw_tick[['time_msc', 'bid', 'ask']].assign(
                    time_msc=lambda d: pd.to_datetime(d['time_msc'], unit='ms')
                ).set_index('time_msc')
            )
            self.__logger.debug(f'df_tick.shape: {df_tick.shape}')
            return df_tick

    @staticmethod
    def _thin_df_tick(df_tick):
        return df_tick.groupby('time').pipe(
            lambda g: g.tail(1).set_index('time').join(
                g.size().to_frame('tick_volume'), how='left'
            )
        )

    def fetch_df_rate(self, granularity='M1', count=10080):
        rates = Mt5.copy_rates_from_pos(
            self.symbol, getattr(Mt5, f'TIMEFRAME_{granularity}'), 0, count
        )
        self.__logger.debug(f'rates: {rates}')
        if not isinstance(rates, np.ndarray):
            raise Mt5ResponseError('Mt5.copy_rates_from_pos() failed.')
        else:
            df_rate = pd.DataFrame(rates).drop(
                columns='real_volume'
            ).assign(
                time=lambda d: pd.to_datetime(d['time'], unit='s')
            ).set_index('time')
            self.__logger.debug(f'df_rate.shape: {df_rate.shape}')
            return df_rate

    def detect_trend_side(self, granularity='D1', count=30):
        lr_coef = self.fetch_df_rate(
            granularity=granularity, count=count
        )[['close']].pipe(
            lambda d:
            scs.linregress(x=(d.index - d.index[0]).days, y=d['close'])
        ).slope
        self.__logger.debug(f'lr_coef: {lr_coef}')
        return ('short' if lr_coef < 0 else 'long')


class AutoTrader(Mt5TraderCore):
    def __init__(self, symbols, hv_granularity='M1', hv_count=10080,
                 hv_ema_span=60, max_spread_ratio=0.01, sleeping_ratio=0,
                 lrr_ema_span=1000, sr_ema_span=1000, significance_level=0.01,
                 volume_factor=0, tick_seconds=3600, day_trend_suppressor=None,
                 interval_seconds=0, retry_count=1, **kwargs):
        super().__init__(symbol=None, **kwargs)
        self.__logger = logging.getLogger(__name__)
        self.symbols = symbols
        self.signal_detector = SignalDetector(
            lrr_ema_span=int(lrr_ema_span), sr_ema_span=int(sr_ema_span),
            significance_level=float(significance_level),
            volume_factor=float(volume_factor)
        )
        self.__tick_seconds = max(
            self.signal_detector.lrr_ema_span,
            self.signal_detector.sr_ema_span, float(tick_seconds)
        )
        self.__hv_granularity = hv_granularity
        self.__hv_count = int(hv_count)
        self.__hv_ema_span = int(hv_ema_span)
        self.__max_spread_ratio = float(max_spread_ratio)
        self.__sleeping_ratio = float(sleeping_ratio)
        self.__interval_seconds = float(interval_seconds)
        self.__day_trend_suppressor = int(day_trend_suppressor or 0)
        self.__retry_count = int(retry_count)
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def invoke(self):
        self.print_log('!!! OPEN DEALS !!!')
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        while True:
            for s in self.symbols:
                self.symbol = s
                for r in range(self.__retry_count + 1):
                    try:
                        self.refresh_mt5_caches()
                        self.make_decision()
                    except Mt5ResponseError as e:
                        if r < self.__retry_count:
                            self.__logger.warning(
                                f'Retry due to an MT5 response error: {e}'
                            )
                        else:
                            raise e
                    else:
                        break
            time.sleep(self.__interval_seconds)

    def make_decision(self):
        st = self.determine_sig_state()
        new_volume = self.design_and_place_order(act=st['act'])
        if new_volume != 0:
            st['state'] = st['state'].replace(
                '-> ',
                '-> {:.1f}% '.format(
                    round(
                        (
                            self.min_margins[
                                {'long': 'ask', 'short': 'bid'}[st['act']]
                            ] / self.symbol_info.volume_min * new_volume
                            / self.account_info.equity * 100
                        ),
                        1
                    )
                )
            )
        elif st['act'] in ['long', 'short']:
            st['state'] = 'LACK OF FUNDS'
        else:
            pass
        self.print_state_line(
            add_str=(st['log_str'] + '{:^27}|'.format(st['state']))
        )

    def determine_sig_state(self):
        pos_pct = '{:.1f}%'.format(
            round(
                (
                    abs(
                        self.position_volumes['long']
                        - self.position_volumes['short']
                    ) / self.symbol_info.volume_min
                    * self.min_margins[
                        {'long': 'ask', 'short': 'bid'}[self.position_side]
                    ] / self.account_info.equity * 100
                ),
                1
            ) if self.position_side else 0
        )
        trend_side = (
            self.detect_trend_side(count=self.__day_trend_suppressor)
            if self.__day_trend_suppressor else None
        )
        df_tick = self.fetch_df_tick(tick_seconds=self.__tick_seconds)
        sig = self.signal_detector.detect(
            df_tick=df_tick, position_side=self.position_side
        )
        if self._has_few_ticks(df_tick=df_tick):
            act = None
            state = 'FEW TICKS ({})'.format(df_tick.shape[0] - 1)
        elif (self.position_side
              and (sig['act'] == 'closing'
                   or (trend_side and sig['act'] != trend_side))):
            act = 'closing'
            state = '{0} {1} ->'.format(pos_pct, self.position_side.upper())
        elif int(self.account_info.equity) == 0:
            act = None
            state = 'NO FUND'
        elif (self.position_side
              and ((sig['act'] and sig['act'] == self.position_side)
                   or not sig['act'])):
            act = None
            state = '{0} {1}'.format(pos_pct, self.position_side.upper())
        elif self.is_margin_lack():
            act = None
            state = 'LACK OF FUNDS'
        elif self._has_over_spread():
            act = None
            state = 'OVER-SPREAD'
        elif sig['act'] != 'closing' and self._has_low_volume():
            act = None
            state = 'LOW VOLUME'
        elif not sig['act']:
            act = None
            state = '-'
        elif trend_side and sig['act'] != trend_side:
            act = None
            state = 'CONTRARY TREND'
        elif self.position_side:
            act = sig['act']
            state = '{0} {1} -> {2}'.format(
                pos_pct, self.position_side.upper(), sig['act'].upper()
            )
        else:
            act = sig['act']
            state = '-> {}'.format(sig['act'].upper())
        return {
            'act': act, 'state': state,
            **{('sig_act' if k == 'act' else k): v for k, v in sig.items()}
        }

    def _has_few_ticks(self, df_tick):
        return (
            df_tick.shape[0] <= max(
                self.signal_detector.lrr_ema_span,
                self.signal_detector.sr_ema_span
            ) * 2
        )

    def _has_over_spread(self):
        spread_ratio = (
            (self.symbol_info_tick.ask - self.symbol_info_tick.bid)
            / (self.symbol_info_tick.ask + self.symbol_info_tick.bid) * 2
        )
        self.__logger.debug(f'spread_ratio: {spread_ratio}')
        return (spread_ratio >= self.__max_spread_ratio)

    def _has_low_volume(self):
        return self.fetch_df_rate(
            granularity=self.__hv_granularity, count=self.__hv_count
        ).pipe(
            lambda d:
            d['tick_volume'].ewm(span=self.__hv_ema_span, adjust=False).mean()
        ).pipe(
            lambda s: (s.iloc[-1] < s.quantile(self.__sleeping_ratio))
        )
