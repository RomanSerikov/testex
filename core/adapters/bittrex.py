import codecs
import hashlib
import requests
import hmac
import simplejson as json
from uuid import uuid4, UUID
from flask import request
from enum import Enum
from decimal import Decimal, InvalidOperation
from cachetools import TTLCache, cached
from datetime import datetime
from bson.decimal128 import Decimal128

from core.helpers import ApiError, OrderStatus, OrderDirection
from core.database import mongo

MIN_TRADE_VALUE = Decimal('0.001')  # BTC
TRADE_FEE_PCT = Decimal('0.0025')


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


class BittrexErrorMessage(Enum):
    MARKET_NOT_PROVIDED = 'MARKET_NOT_PROVIDED'
    NONCE_NOT_PROVIDED = 'NONCE_NOT_PROVIDED'
    APIKEY_NOT_PROVIDED = 'APIKEY_NOT_PROVIDED'
    APISIGN_NOT_PROVIDED = 'APISIGN_NOT_PROVIDED'
    RATE_NOT_PROVIDED = 'RATE_NOT_PROVIDED'
    QUANTITY_NOT_PROVIDED = 'QUANTITY_NOT_PROVIDED'
    APIKEY_INVALID = 'APIKEY_INVALID'
    INVALID_SIGNATURE = 'INVALID_SIGNATURE'
    INVALID_MARKET = 'INVALID_MARKET'
    QUANTITY_INVALID = 'QUANTITY_INVALID'
    RATE_INVALID = 'RATE_INVALID'
    MIN_TRADE_REQUIREMENT_NOT_MET = 'MIN_TRADE_REQUIREMENT_NOT_MET'
    DUST_TRADE_DISALLOWED_MIN_VALUE_50K_SAT = 'DUST_TRADE_DISALLOWED_MIN_VALUE_50K_SAT'
    INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS'
    ORDER_NOT_OPEN = 'ORDER_NOT_OPEN'
    UUID_NOT_PROVIDED = 'UUID_NOT_PROVIDED'
    UUID_INVALID = 'UUID_INVALID'
    INVALID_ORDER = 'INVALID_ORDER'


class BittrexApiError(ApiError):

    def __init__(self, message, *args, **kwargs):
        super(BittrexApiError, self).__init__(*args, **kwargs)
        self.message = message

    def get_response(self):
        return dict(
            success=False,
            message=self.message,
            result=None
        )


def get_response(result):
    return dict(
        success=True,
        message='',
        result=result
    )


def prep_t(string):
    return 'T{}'.format(string)


def prep_t_market(market):
    return '-'.join(map(prep_t, market.split('-')))


def trim_t(string):
    return string[1:] if string.startswith('T') else string


def trim_t_market(market):
    return '-'.join(map(trim_t, market.split('-')))


@cached(TTLCache(ttl=3600, maxsize=128))
def get_markets():
    res = requests.get('https://bittrex.com/api/v1.1/public/getmarkets')
    data = json.loads(res.text, use_decimal=True)
    markets = {
        item['MarketName']: item
        for item in data['result']
    }
    return markets


def get_api_key():
    if not request.args.get('nonce'):
        raise BittrexApiError(BittrexErrorMessage.NONCE_NOT_PROVIDED.value)

    if not request.args.get('apikey'):
        raise BittrexApiError(BittrexErrorMessage.APIKEY_NOT_PROVIDED.value)

    apikey = request.args['apikey']
    apisecret = apikey  # TODO: check api key existence in the future and get secret and all other settings
    apisign = request.headers.get('apisign')
    if not apisign:
        raise BittrexApiError(BittrexErrorMessage.APISIGN_NOT_PROVIDED.value)

    signature = hmac.new(
        key=codecs.encode(apisecret),
        msg=codecs.encode(request.url, 'utf-8'),
        digestmod=hashlib.sha512
    ).hexdigest()
    if signature != apisign:
        raise BittrexApiError(BittrexErrorMessage.INVALID_SIGNATURE.value)

    return apikey


def get_market(optional=False):
    if not request.args.get('market'):
        if optional:
            return
        raise BittrexApiError(BittrexErrorMessage.MARKET_NOT_PROVIDED.value)

    market = trim_t(request.args['market'])
    markets = get_markets()
    if market not in markets:
        raise BittrexApiError(BittrexErrorMessage.INVALID_MARKET.value)

    return market


def get_amount():
    if not request.args.get('quantity'):
        raise BittrexApiError(BittrexErrorMessage.QUANTITY_NOT_PROVIDED.value)

    try:
        amount = Decimal(request.args['quantity'])
    except InvalidOperation:
        raise BittrexApiError(BittrexErrorMessage.QUANTITY_INVALID.value)

    return amount


def get_price():
    if not request.args.get('rate'):
        raise BittrexApiError(BittrexErrorMessage.RATE_NOT_PROVIDED.value)

    try:
        price = Decimal(request.args['rate'])
    except InvalidOperation:
        raise BittrexApiError(BittrexErrorMessage.RATE_INVALID.value)

    return price


def get_order_number():
    if not request.args.get('uuid'):
        raise BittrexApiError(BittrexErrorMessage.UUID_NOT_PROVIDED.value)

    try:
        UUID(request.args['uuid'])
    except ValueError:
        raise BittrexApiError(BittrexErrorMessage.UUID_INVALID.value)

    return request.args['uuid']


def send_order(direction):
    api_key = get_api_key()
    market = get_market()
    amount = get_amount()
    price = get_price()

    min_trade_size = get_markets()[market]['MinTradeSize']
    if amount < min_trade_size:
        raise BittrexApiError(BittrexErrorMessage.MIN_TRADE_REQUIREMENT_NOT_MET.value)

    if amount * price < MIN_TRADE_VALUE:
        raise BittrexApiError(BittrexErrorMessage.DUST_TRADE_DISALLOWED_MIN_VALUE_50K_SAT.value)

    order = dict(
        _id=str(uuid4()),
        _user=api_key,
        opened_at=datetime.utcnow(),
        direction=direction,
        amount=Decimal128(amount),
        price=Decimal128(price),
        market=market,
        status=OrderStatus.OPENED.value
    )
    # TODO: connection reset here (with prob)
    mongo.db.orders.insert_one(order)
    # TODO: and here (with prob too)

    return get_response(dict(uuid=order['_id']))


def cancel_order():
    api_key = get_api_key()
    number = get_order_number()
    query = dict(_id=number, _user=api_key)

    order = mongo.db.orders.find_one(query)
    if not order:
        raise BittrexApiError(BittrexErrorMessage.INVALID_ORDER.value)

    if order['status'] != OrderStatus.OPENED.value:
        raise BittrexApiError(BittrexErrorMessage.ORDER_NOT_OPEN.value)

    mongo.db.orders.update_one(
        query,
        dict(
            status=OrderStatus.CANCELED.value,
            closed_at=datetime.utcnow()
        ),
        upsert=False
    )

    return get_response(None)


def format_datetime(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]


def order_get_decimal(order, key, default=Decimal()) -> Decimal:
    value = order.get(key)
    return value.to_decimal() if value else default


def format_open_order(order) -> dict:
    amount = order_get_decimal(order, 'amount')
    result = {
        'CancelInitiated': False,  # TODO: implement
        'Closed': None,
        'CommissionPaid': order_get_decimal(order, 'fee'),
        'Condition': 'NONE',
        'ConditionTarget': None,
        'Exchange': order['market'],
        'ImmediateOrCancel': False,
        'IsConditional': False,
        'Limit': order_get_decimal(order, 'price'),
        'Opened': format_datetime(order['opened_at']),
        'OrderType': BittrexOrderType.from_direction(order['direction']),
        'OrderUuid': order['_id'],
        'Price': Decimal(),
        'PricePerUnit': None,
        'Quantity': amount,
        'QuantityRemaining': amount - order_get_decimal(order, 'executed_amount'),
        'Uuid': None
    }
    return result


def format_history_order(order) -> dict:
    amount = order_get_decimal(order, 'amount')
    result = {
        'Closed': format_datetime(order['closed_at']),
        'Commission': order_get_decimal(order, 'fee'),
        'Condition': 'NONE',
        'ConditionTarget': None,
        'Exchange': order['market'],
        'ImmediateOrCancel': False,
        'IsConditional': False,
        'Limit': order_get_decimal(order, 'price'),
        'OrderType': BittrexOrderType.from_direction(order['direction']),
        'OrderUuid': order['_id'],
        'Price': order_get_decimal(order, 'total'),
        'PricePerUnit': order_get_decimal(order, 'executed_price'),
        'Quantity': amount,
        'QuantityRemaining': amount - order_get_decimal(order, 'executed_amount'),
        'TimeStamp': format_datetime(order['opened_at'])
    }
    return result


def format_single_order(order) -> dict:
    is_closed = order['status'] in [OrderStatus.FILLED.value, OrderStatus.CANCELED.value]
    price = order_get_decimal(order, 'price')
    amount = order_get_decimal(order, 'amount')
    fee = order_get_decimal(order, 'fee')
    reserved = price * amount
    fee_reserved = reserved * TRADE_FEE_PCT
    executed_amount = order_get_decimal(order, 'executed_amount')
    result = {
        'AccountId': None,
        'CancelInitiated': False,
        'Closed': format_datetime(order['closed_at']) if is_closed else None,
        'CommissionPaid': fee,
        'CommissionReserveRemaining': fee_reserved - fee,
        'CommissionReserved': fee_reserved,
        'Condition': 'NONE',
        'ConditionTarget': None,
        'Exchange': order['market'],
        'ImmediateOrCancel': False,
        'IsConditional': False,
        'IsOpen': not is_closed,
        'Limit': price,
        'Opened': format_datetime(order['opened_at']),
        'OrderUuid': order['_id'],
        'Price': order_get_decimal(order, 'total'),
        'PricePerUnit': order_get_decimal(order, 'executed_price', None),
        'Quantity': amount,
        'QuantityRemaining': amount - executed_amount,
        'ReserveRemaining': reserved - executed_amount * price,
        'Reserved': reserved,
        'Sentinel': str(uuid4()),  # TODO: what is this
        'Type': BittrexOrderType.from_direction(order['direction']),
    }
    return result


def get_open_orders():
    api_key = get_api_key()
    query = dict(_user=api_key, status=OrderStatus.OPENED.value)

    market = get_market(optional=True)
    if market:
        query['market'] = market

    orders = mongo.db.orders.find(query)

    return get_response(list(map(format_open_order, orders)))


def get_order():
    api_key = get_api_key()
    number = get_order_number()

    order = mongo.db.find_one(dict(_id=number, _user=api_key))
    if not order:
        raise BittrexApiError(BittrexErrorMessage.INVALID_ORDER.value)

    return get_response(format_single_order(order))


def get_order_history():
    api_key = get_api_key()
    query = dict(_user=api_key, status=OrderStatus.FILLED.value)

    market = get_market(optional=True)
    if market:
        query['market'] = market

    orders = mongo.db.orders.find(query)

    return get_response(list(map(format_history_order, orders)))
