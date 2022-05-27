#!/usr/bin/env python

import logging
import os
from pprint import pformat

import MetaTrader5 as Mt5

from .util import Mt5ResponseError, print_json


def close_positions(symbol, dry_run=False):
    logger = logging.getLogger(__name__)
    logger.info(f'symbol: {symbol}, dry_run: {dry_run}')
    positions = Mt5.positions_get(symbol=symbol)
    logger.debug(f'positions: {positions}')
    if not positions:
        logger.info(f'No position for {symbol}.')
    else:
        for p in positions:
            _send_or_check_order(
                request={
                    'action': Mt5.TRADE_ACTION_DEAL,
                    'symbol': p.symbol, 'volume': p.volume,
                    'type': (
                        Mt5.ORDER_TYPE_SELL if p.type == Mt5.POSITION_TYPE_BUY
                        else Mt5.ORDER_TYPE_BUY
                    ),
                    'type_filling': Mt5.ORDER_FILLING_FOK,
                    'type_time': Mt5.ORDER_TIME_GTC,
                    'position': p.ticket
                },
                only_check=dry_run
            )


def _send_or_check_order(request, only_check=False):
    logger = logging.getLogger(__name__)
    logger.debug(f'request: {request}')
    order_func = 'order_{}'.format('check' if only_check else 'send')
    result = getattr(Mt5, order_func)(request)
    logger.debug(f'result: {result}')
    response = {
        k: (v._asdict() if k == 'request' else v)
        for k, v in result._asdict().items()
    }
    print_json(response)
    if (((not only_check) and result.retcode == Mt5.TRADE_RETCODE_DONE)
            or (only_check and result.retcode == 0)):
        logger.info(f'response:{os.linesep}' + pformat(response))
    else:
        logger.error(f'response:{os.linesep}' + pformat(response))
        raise Mt5ResponseError(
            f'Mt5.{order_func}() failed. <= `{result.comment}`'
        )
