from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
from config import config, Config

db = SQLAlchemy()
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    celery.conf.update(app.config)

    from .auth import auth as auth_blueprint
    from .assets import assets as assets_blueprint
    from .action import action as action_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(assets_blueprint, url_prefix='/assets')
    app.register_blueprint(action_blueprint, url_prefix='/action')

    return app
