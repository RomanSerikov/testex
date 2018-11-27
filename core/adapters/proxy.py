from cachetools import TTLCache, cached

from core.adapters.wrapper import BittrexApi


class BittrexApiProxy(BittrexApi):

    @cached(TTLCache(ttl=3600, maxsize=128))
    def get_markets(self):
        return self.public.getmarkets()

    @cached(TTLCache(ttl=3600, maxsize=128))
    def get_currencies(self):
        return self.public.getcurrencies()

    @cached(TTLCache(ttl=5, maxsize=128))
    def get_ticker(self, market):
        return self.public.getticker(market=market)

    @cached(TTLCache(ttl=60, maxsize=128))
    def get_market_summaries(self):
        return self.public.getmarketsummaries()

    @cached(TTLCache(ttl=60, maxsize=128))
    def get_market_summary(self, market):
        return self.public.getmarketsummary(market=market)

    @cached(TTLCache(ttl=5, maxsize=128))
    def get_order_book(self, market, _type='both'):
        return self.public.getorderbook(market=market, type=_type)

    @cached(TTLCache(ttl=5, maxsize=128))
    def get_market_history(self, market):
        return self.public.getmarkethistory(market=market)

    @cached(TTLCache(ttl=3600, maxsize=128))
    def get_ticks(self, market, tick_interval='day'):
        return self.public_v2.GetTicks(marketName=market, tickInterval=tick_interval)
