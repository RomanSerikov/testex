import codecs
import hashlib
import hmac
import requests
import simplejson as json
from decimal import Decimal
from urllib.parse import urlencode, urljoin
from datetime import datetime
from enum import Enum

from core.helpers import ApiError


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


class BittrexApiSegment:

    def __init__(self, api_host, path, api_key=None, api_secret=None):
        self.base_url = api_host + path
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_nonce = 0

    def get_nonce(self):
        nonce = int(datetime.utcnow().timestamp() * 1000)
        if self.last_nonce == nonce:
            nonce += 1
        self.last_nonce = nonce
        return nonce

    def get_apisign(self, uri: str):
        return hmac.new(
            key=codecs.encode(self.api_secret),
            msg=codecs.encode(uri, 'utf-8'),
            digestmod=hashlib.sha512
        ).hexdigest()

    def request(self, method: str, **params):
        url = urljoin(self.base_url, method)
        headers = {
            'Content-Type': 'application/json'
        }
        not_none_params = {
            k: v
            for k, v in params.items()
            if v is not None
        }

        if self.api_key:
            not_none_params.update(
                nonce=self.get_nonce(),
                apikey=self.api_key
            )
            headers.update(
                apisign=self.get_apisign('{}?{}'.format(url, urlencode(not_none_params)))
            )

        res = requests.get(url, headers=headers, params=not_none_params)
        if res.status_code in [200, 201]:
            data = json.loads(res.text, use_decimal=True)
        else:
            raise requests.HTTPError(res.status_code)

        return data

    def __getattr__(self, request_method):
        def method(*_args, **kwargs):
            return self.request(request_method, **kwargs)
        return method


# Based on https://bittrex.zendesk.com/hc/en-us/articles/115003723911-Developer-s-Guide-API
class BittrexApi:

    def __init__(self, api_key=None, api_secret=None, api_host='https://bittrex.com/'):
        self.public = BittrexApiSegment(api_host, 'api/v1.1/public/')
        self.public_v2 = BittrexApiSegment(api_host, 'Api/v2.0/pub/market/')
        self.market = BittrexApiSegment(api_host, 'api/v1.1/market/', api_key=api_key, api_secret=api_secret)
        self.account = BittrexApiSegment(api_host, 'api/v1.1/account/', api_key=api_key, api_secret=api_secret)

    # Public API

    def get_markets(self):
        return self.public.getmarkets()

    def get_currencies(self):
        return self.public.getcurrencies()

    def get_ticker(self, market):
        return self.public.getticker(market=market)

    def get_market_summaries(self):
        return self.public.getmarketsummaries()

    def get_market_summary(self, market):
        return self.public.getmarketsummary(market=market)

    def get_order_book(self, market, _type='both'):
        return self.public.getorderbook(market=market, type=_type)

    def get_market_history(self, market):
        return self.public.getmarkethistory(market=market)

    def get_ticks(self, market, tick_interval='day'):
        return self.public_v2.GetTicks(marketName=market, tickInterval=tick_interval)

    # Market API

    def buy_limit(self, market, quantity: Decimal, rate: Decimal):
        return self.market.buylimit(market=market, quantity=quantity, rate=rate)

    def sell_limit(self, market, quantity: Decimal, rate: Decimal):
        return self.market.selllimit(market=market, quantity=quantity, rate=rate)

    def cancel(self, uuid):
        return self.market.cancel(uuid=uuid)

    def get_open_orders(self, market=None):
        return self.market.getopenorders(market=market)

    # Account API

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
