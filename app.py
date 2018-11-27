import logging
from flask import Flask
from werkzeug.utils import find_modules, import_string

from core.cache import cache
from core.database import mongo


def create_app(config_filename='config/dev.py'):
    app = Flask(__name__)
    app.config.from_pyfile(config_filename)

    cache.init_app(app)
    mongo.init_app(app)

    for module_name in find_modules('blueprints', recursive=True):
        try:
            blueprint = import_string('{}.blueprint'.format(module_name))
            app.register_blueprint(blueprint)
        except ImportError:
            pass
        else:
            logging.debug('registered {}'.format(module_name))

    return app


if __name__ == '__main__':
    create_app().run()
