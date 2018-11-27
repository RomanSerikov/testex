from flask import Blueprint, current_app

from core.helpers import api_method
from core.adapters.bittrex import get_order_history, get_order

blueprint = Blueprint('bittrex_account_v1.1', __name__, url_prefix='/bittrex.com/api/v1.1/account')


@blueprint.route('/getbalances')
def getbalances():
    if current_app.config['INFINITE_BALANCES']:
        return dict()
    return dict()


@blueprint.route('/getbalance')
def getbalance():
    pass


@blueprint.route('/getdepositaddress')
def getdepositaddress():
    pass


@blueprint.route('/withdraw')
def withdraw():
    pass


@blueprint.route('/getorder')
def getorder():
    return get_order()


@blueprint.route('/getorderhistory')
@api_method
def getorderhistory():
    return get_order_history()


@blueprint.route('/getwitdrawalhistory')
def getwitdrawalhistory():
    pass


@blueprint.route('/getdeposithistory')
def getdeposithistory():
    pass
