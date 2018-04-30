# -*- coding: utf8 -*-
from functools import wraps
from flask import g, current_app, jsonify


def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def admin_required():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 必须登录, 判断是否属于管理员.
            if g.current_user.email in current_app.config['ADMIN_EMAIL_LIST']:
                return f(*args, **kwargs)
            else:
                return forbidden('Insufficient permissions')
        return decorated_function

    return decorator

