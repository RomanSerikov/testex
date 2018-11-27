from flask import Blueprint

from core.cache import cache
from core.helpers import proxy_request, process_request
from core.adapters.bittrex import prep_t, prep_t_market, trim_t_market

blueprint = Blueprint('bittrex_public_v1.1', __name__, url_prefix='/bittrex.com/api/v1.1/public')


@blueprint.route('/getmarkets', methods=['GET'])
@cache.cached(timeout=60)
def getmarkets():
    return process_request(postprocess_fields=dict(
        BaseCurrency=prep_t,
        MarketCurrency=prep_t,
        MarketName=prep_t_market
    ))


@blueprint.route('/getcurrencies', methods=['GET'])
@cache.cached(timeout=60)
def getcurrencies():
    return process_request(postprocess_fields=dict(Currency=prep_t))


@blueprint.route('/getticker', methods=['GET'])
@cache.cached(timeout=60)
def getticker():
    return proxy_request(preprocess_params=dict(market=trim_t_market))


@blueprint.route('/getmarketsummaries', methods=['GET'])
@cache.cached(timeout=60)
def getmarketsummaries():
    return process_request(postprocess_fields=dict(MarketName=prep_t_market))


@blueprint.route('/getorderbook', methods=['GET'])
@cache.cached(timeout=60)
def getorderbook():
    return proxy_request(preprocess_params=dict(market=trim_t_market))


@blueprint.route('/getmarketsummary', methods=['GET'])
@cache.cached(timeout=60)
def getmarketsummary():
    return proxy_request(preprocess_params=dict(market=trim_t_market))


@blueprint.route('/getmarkethistory', methods=['GET'])
@cache.cached(timeout=3600)
def getmarkethistory():
    return proxy_request(preprocess_params=dict(market=trim_t_market))
