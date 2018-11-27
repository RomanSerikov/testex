from flask import Blueprint

from core.cache import cache
from core.helpers import proxy_request
from blueprints.bittrex.converters import trim_t_market

blueprint = Blueprint('bittrex_account_v2.0', __name__, url_prefix='/bittrex.com/Api/v2.0/pub/market')


@blueprint.route('/GetTicks', methods=['GET'])
@cache.cached(timeout=60)
def get_ticks():
    return proxy_request(preprocess_params=dict(marketName=trim_t_market))
