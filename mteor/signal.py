#!/usr/bin/env python

import logging
import os
from pprint import pformat

import numpy as np
import scipy.stats as scs


class MacdSignalDetector(object):
    def __init__(self, fast_ema_span=12, slow_ema_span=26, macd_ema_span=9,
                 generic_ema_span=1024, significance_level=0.01,
                 trigger_sharpe_ratio=1, signal_count=1):
        assert fast_ema_span < slow_ema_span, 'invalid spans'
        self.__logger = logging.getLogger(__name__)
        self.fast_ema_span = fast_ema_span
        self.slow_ema_span = slow_ema_span
        self.macd_ema_span = macd_ema_span
        self.generic_ema_span = generic_ema_span
        self.significance_level = significance_level
        self.trigger_sharpe_ratio = trigger_sharpe_ratio
        self.signal_count = signal_count
        self.__logger.debug('vars(self):' + os.linesep + pformat(vars(self)))

    def detect(self, df_tick, position_side=None):
        df_sig = self._calculate_adjusted_macd(df_tick=df_tick).pipe(
            lambda d: self._calculate_ewm_sharpe_ratio(
                df_macd=d, span=self.generic_ema_span,
                is_short=(d['macd'].iloc[-1] < d['macd_ema'].iloc[-1])
            )
        ).assign(
            delta_macd_diff=lambda d: (d['macd'] - d['macd_ema']).diff(),
            delta_emsr=lambda d: d['emsr'].diff()
        ).assign(
            delta_macd_diff_ema=lambda d: d['delta_macd_diff'].ewm(
                span=self.generic_ema_span, adjust=False
            ).mean(),
            delta_macd_diff_emvar=lambda d: d['delta_macd_diff'].ewm(
                span=self.generic_ema_span, adjust=False
            ).var(ddof=1),
            delta_emsr_ema=lambda d: d['delta_emsr'].ewm(
                span=self.generic_ema_span, adjust=False
            ).mean(),
            delta_emsr_emvar=lambda d: d['delta_emsr'].ewm(
                span=self.generic_ema_span, adjust=False
            ).var(ddof=1)
        ).tail(self.signal_count)
        sig = (
            df_sig.iloc[-1].to_dict() if df_tick.shape[0] > 0
            else {c: np.nan for c in df_sig.columns}
        )
        delta_macd_diff_emci = scs.t.interval(
            alpha=(1 - self.significance_level),
            df=(self.macd_ema_span - 1), loc=sig['delta_macd_diff_ema'],
            scale=np.sqrt(sig['delta_macd_diff_emvar'] / self.macd_ema_span)
        )
        delta_emsr_emci = scs.t.interval(
            alpha=(1 - self.significance_level),
            df=(self.generic_ema_span - 1), loc=sig['delta_emsr_ema'],
            scale=np.sqrt(sig['delta_emsr_emvar'] / self.generic_ema_span)
        )
        if (df_sig['macd'] > df_sig['macd_ema']).all():
            if ((df_sig['emsr'] > 0).all()
                    and sig['delta_macd_diff_ema'] > 0
                    and sig['delta_emsr_ema'] > 0
                    and (delta_macd_diff_emci[0] > 0
                         or delta_emsr_emci[0] > 0
                         or sig['emsr'] >= self.trigger_sharpe_ratio)):
                act = 'long'
            elif ((position_side == 'long' and (df_sig['emsr'] < 0).all()
                   and (delta_macd_diff_emci[1] < 0 or delta_emsr_emci[1] < 0))
                  or position_side == 'short'):
                act = 'closing'
            else:
                act = None
        elif (df_sig['macd'] < df_sig['macd_ema']).all():
            if ((df_sig['emsr'] > 0).all()
                    and sig['delta_macd_diff_ema'] < 0
                    and sig['delta_emsr_ema'] > 0
                    and (delta_macd_diff_emci[1] < 0
                         or delta_emsr_emci[0] > 0
                         or sig['emsr'] >= self.trigger_sharpe_ratio)):
                act = 'short'
            elif ((position_side == 'short' and (df_sig['emsr'] < 0).all()
                   and (delta_macd_diff_emci[0] > 0 or delta_emsr_emci[1] < 0))
                  or position_side == 'long'):
                act = 'closing'
            else:
                act = None
        else:
            act = None
        return {
            'act': act, **sig,
            'delta_macd_diff_emci_lower': delta_macd_diff_emci[0],
            'delta_macd_diff_emci_upper': delta_macd_diff_emci[1],
            'delta_emsr_emci_lower': delta_emsr_emci[0],
            'delta_emsr_emci_upper': delta_emsr_emci[1],
            'log_str': '{0:^41}|{1:^35}|'.format(
                'MACD-EMA:{0:>10}{1:>18}'.format(
                    '{:.1g}'.format(sig['macd'] - sig['macd_ema']),
                    np.array2string(
                        np.array(delta_macd_diff_emci),
                        formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                ),
                'EMSR:{0:>9}{1:>17}'.format(
                    '{:.1g}'.format(sig['emsr']),
                    np.array2string(
                        np.array(delta_emsr_emci),
                        formatter={'float_kind': lambda f: f'{f:.1g}'}
                    )
                )
            )
        }

    def _calculate_adjusted_macd(self, df_tick):
        return df_tick.dropna(subset=['ask', 'bid']).reset_index().assign(
            mid=lambda d: d[['ask', 'bid']].mean(axis=1),
            delta_sec=lambda d: d['time_msc'].diff().dt.total_seconds()
        ).set_index('time_msc').assign(
            macd=lambda d: (
                d['mid'].ewm(span=self.fast_ema_span, adjust=False).mean()
                - d['mid'].ewm(span=self.slow_ema_span, adjust=False).mean()
            ) / d['delta_sec'] * d['delta_sec'].mean()
        ).assign(
            macd_ema=lambda d:
            d['macd'].ewm(span=self.macd_ema_span, adjust=False).mean()
        )

    @staticmethod
    def _calculate_ewm_sharpe_ratio(df_macd, span=None, is_short=False):
        return df_macd.assign(
            spread=lambda d: (d['ask'] - d['bid'])
        ).assign(
            return_rate=lambda d: (
                (np.exp(np.log(d['mid']).diff()) - 1) * (-1 if is_short else 1)
                / d['delta_sec'] * d['delta_sec'].mean()
                / d['spread'] * d['spread'].mean()
            )
        ).assign(
            emsr=lambda d: (
                d['return_rate'].ewm(span=span, adjust=False).mean()
                / d['return_rate'].ewm(span=span, adjust=False).std(ddof=1)
            )
        )

    def _calculate_ewm_log_return_velocity(self, df_tick, span=None):
        return df_tick.reset_index().assign(
            lrv=lambda d: (
                np.log(d[['ask', 'bid']].mean(axis=1)).diff()
                / d['time_msc'].diff().dt.total_seconds()
            )
        ).assign(
            lrv=lambda d: d['log_return'] / d['delta_sec']
        ).assign(
            lrv_ema=lambda d: d['lrv'].ewm(span=span, adjust=False).mean(),
            lrv_emvar=lambda d:
            d['lrv'].ewm(span=span, adjust=False).var(ddof=1)
        )
