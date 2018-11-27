import requests
import simplejson as json
from flask import current_app, request, jsonify, Response
from functools import wraps
from enum import Enum


class OrderDirection(Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(Enum):
    OPENED = 'opened'
    CANCELED = 'canceled'
    FILLED = 'filled'


class ApiError(Exception):

    def get_response(self):
        raise NotImplementedError


def proxy_request(preprocess_params=None):
    params = request.args.to_dict()
    if current_app.config['TESTNET_SYMBOLS'] and preprocess_params:
        for key, preprocessor in preprocess_params.items():
            params[key] = preprocessor(params[key])

    res = requests.get('https:/{}'.format(request.path), params=params)
    return Response(res.content, content_type=res.headers['content-type'])


def process_request(postprocess_fields: dict):
    res = requests.get('https:/{}'.format(request.path))
    if current_app.config['TESTNET_SYMBOLS']:
        data = json.loads(res.text, use_decimal=True)
        if data['success']:
            for item in data['result']:
                for field, processor in postprocess_fields.items():
                    item[field] = processor(item[field])
        return jsonify(data)
    return Response(res.content, content_type=res.headers['content-type'])


def api_method(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            response = f(*args, **kwargs)
        except ApiError as e:
            response = e.get_response()
        return jsonify(response)
    return decorated_function
