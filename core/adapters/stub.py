from decimal import Decimal
from cachetools import TTLCache, cached
from enum import Enum
from uuid import uuid4
from bson import Decimal128
from datetime import datetime

from core.adapters.wrapper import BittrexApi, BittrexApiError, BittrexErrorMessage
from core.helpers import OrderDirection, OrderStatus


class BittrexOrderType(Enum):
    BUY_LIMIT = 'BUY_LIMIT'
    SELL_LIMIT = 'SELL_LIMIT'

    @staticmethod
    def from_direction(direction):
        mapping = {
            OrderDirection.BUY.value: BittrexOrderType.BUY_LIMIT.value,
            OrderDirection.SELL.value: BittrexOrderType.SELL_LIMIT.value
        }
        return mapping[direction]


def make_response(result):
    return dict(
        success=True,
        message='',
        result=result
    )


class BittrexApiStub(BittrexApi):
    min_trade_value = Decimal('0.001')  # BTC

    @property
    @cached(TTLCache(ttl=3600, maxsize=128))
    def markets(self) -> dict:
        data = self.public.getmarkets()
        return {
            item['Market']: item
            for item in data['result']
        }

    def send_order(self, direction, market, quantity: Decimal, rate: Decimal):
        min_trade_size = self.markets[market]['MinTradeSize']
        if quantity < min_trade_size:
            raise BittrexApiError(BittrexErrorMessage.MIN_TRADE_REQUIREMENT_NOT_MET.value)

        if quantity * rate < self.min_trade_value:
            raise BittrexApiError(BittrexErrorMessage.DUST_TRADE_DISALLOWED_MIN_VALUE_50K_SAT.value)

        order = dict(
            _id=str(uuid4()),
            _user=api_key,
            opened_at=datetime.utcnow(),
            direction=direction,
            amount=Decimal128(quantity),
            price=Decimal128(rate),
            market=market,
            status=OrderStatus.OPENED.value
        )
        # TODO: connection reset here (with prob)
        mongo.db.orders.insert_one(order)
        # TODO: and here (with prob too)

        return make_response(dict(uuid=order['_id']))

    def buy_limit(self, market, quantity: Decimal, rate: Decimal):
        return self.send_order(direction=OrderDirection.BUY.value, market=market, quantity=quantity, rate=rate)

    def sell_limit(self, market, quantity: Decimal, rate: Decimal):
        return self.send_order(direction=OrderDirection.SELL.value, market=market, quantity=quantity, rate=rate)

    def cancel(self, uuid):
        return self.market.cancel(uuid=uuid)

    def get_open_orders(self, market=None):
        return self.market.getopenorders(market=market)

    def get_balances(self):
        return self.account.getbalances()

    def get_balance(self, currency):
        return self.account.getbalance(currency=currency)

    def get_deposit_address(self, currency):
        return self.account.getdepositaddress(currency=currency)

    def withdraw(self, currency, quantity: Decimal, address):
        return self.account.withdraw(currency=currency, quantity=quantity, address=address)

    def get_order(self, uuid):
        return self.account.getorder(uuid=uuid)

    def get_order_history(self, market=None):
        return self.account.getorderhistory(market=market)

    def get_withdrawal_history(self, currency=None):
        return self.account.getwithdrawalhistory(currency=currency)

    def get_deposit_history(self, currency=None):
        return self.account.getdeposithistory(currency=currency)
