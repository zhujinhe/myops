import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'htgs'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DB_USER = 'ops_user'
    DB_PASSWORD = 'ops_pass'
    ADMIN_EMAIL_LIST = ['zhujinhe@vip.qq.com']

    # aliyun
    aliyun_region = ['cn-hangzhou', 'cn-beijing']
    # aliyun readonly access_key/secret
    aliyun_readonly_access_key = 'my_access_key'
    aliyun_readonly_secret = 'my_secret'
    # aliyun full access access_key/secret
    aliyun_full_access_key = 'my_full_access_key'
    aliyun_full_secret = 'my_full_secret'

    # DNSPod api access key
    dnspod_domain = 'https://dnsapi.cn/'
    dnspod_token = 'my_token'
    ops_domain = 'ops.com'

    # yuntongxun
    yuntongxun_username = 'foo@ops.com'
    yuntongxun_password = 'bar@pass'

    # saltstack netapi
    salt_url = 'https://saltnetapi.ops.com:8000'
    salt_pam_username = 'saltnetapi'
    salt_pam_password = 'password'

    # celery
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_TIMEZONE = 'Asia/Shanghai'
    CELERY_DEFAULT_QUEUE = 'ops_ops'

    # task flow
    TASKFLOW_DATABASE_URI = os.environ.get('DE_TASKFLOW_URL') or \
                            'mysql://%s:%s@localhost/ops_taskflow' % (DB_USER, DB_PASSWORD)

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DE_DATABASE_URL') or \
                              'mysql://%s:%s@localhost/ops' % (Config.DB_USER, Config.DB_PASSWORD)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DE_DATABASE_URL') or \
                              'mysql://%s:%s@localhost/ops_test' % (Config.DB_USER, Config.DB_PASSWORD)
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost:5000'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DE_DATABASE_URL') or \
                              'mysql://%s:%s@localhost/ops' % (Config.DB_USER, Config.DB_PASSWORD)

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # logging errors to files
        # Usage: bash> export FLASK_CONFIG='production'
        # current_app.logger.debug("no context_update provided")
        import logging
        from logging.handlers import RotatingFileHandler
        logging_location = 'logs/debug.log'
        logging_level = logging.DEBUG
        logging_format = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
        file_handler = RotatingFileHandler(filename=logging_location)
        file_handler.setLevel(logging_level)
        file_handler.setFormatter(logging_format)
        app.logger.addHandler(file_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
