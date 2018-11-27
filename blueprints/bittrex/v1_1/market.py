from flask import Blueprint

from core.helpers import api_method, OrderDirection
from core.adapters.bittrex import send_order, cancel_order, get_open_orders

blueprint = Blueprint('bittrex_market_v1.1', __name__, url_prefix='/bittrex.com/api/v1.1/market')


@blueprint.route('/buylimit', methods=['GET'])
@api_method
def buylimit():
    return send_order(OrderDirection.BUY.value)


@blueprint.route('/selllimit')
@api_method
def selllimit():
    return send_order(OrderDirection.SELL.value)


@blueprint.route('/cancel')
@api_method
def cancel():
    return cancel_order()


@blueprint.route('/getopenorders')
@api_method
def getopenorders():
    return get_open_orders()
