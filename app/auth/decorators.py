# -*- coding: utf8 -*-
from functools import wraps
from flask import g, current_app, jsonify


def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def permission_required(action=None, resource=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 必须登录, 如果是管理员, 不做任何策略认证.
            if g.current_user.email in current_app.config['ADMIN_EMAIL_LIST']:
                return f(*args, **kwargs)

            # 其他用户根据所属用户和组的组合policies进行逻辑判断.优先deny.
            verification_result = False

            policy_documents = [p.default_document for p in g.current_user.list_all_policies()]
            for document in policy_documents:
                # 验证策略格式
                # TODO: 验证权限是否满足.并修改认证结果.
                pass

            if not verification_result:
                return forbidden('Insufficient permissions')
            else:
                return f(*args, **kwargs)

        return decorated_function

    return decorator
