# -*- coding: utf8 -*-
from flask import request, jsonify, g, current_app
from flask_httpauth import HTTPBasicAuth
from .models import User, Group, Policy
from .decorators import admin_required
from .. import db
from . import auth
from app.exceptions import ValidationError
from datetime import datetime
from .errors import unauthorized

basic_auth = HTTPBasicAuth()


@basic_auth.error_handler
def basic_auth_error():
    return unauthorized('Invalid credentials')


@basic_auth.verify_password
def verify_credential(email_or_token, password):
    """
    如果提供密码,则按照账号密码认证,如果密码为空,则按照token认证
    :param email_or_token:
    :param password:
    :return:
    """
    if password == '':
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)


@basic_auth.login_required
def is_admin():
    if g.current_user.email in current_app.config['ADMIN_EMAIL_LIST']:
        return True
    else:
        return False


@auth.route('/users/', methods=['GET'])
@basic_auth.login_required
def get_users():
    return jsonify({'users': [user.export_data() for user in User.query.all()]})


@auth.route('/users/<string:email>/', methods=['GET'])
@basic_auth.login_required
def get_user_by_email(email):
    """
    根据email查询用户
    :param email:
    :return:
    """
    user = User.query.filter_by(email=email).first_or_404()
    return jsonify(user.export_data())


@auth.route('/users/<string:email>/groups/', methods=['GET'])
@basic_auth.login_required
def get_groups_of_user(email):
    """
    根据email查询用户所属于的所有组
    :param email:
    :return:
    """
    return jsonify([group.export_data() for group in User.query.filter_by(email=email).first_or_404().groups])


@auth.route('/users/<string:email>/policies/', methods=['GET'])
@basic_auth.login_required
def get_policies_of_user(email):
    """
    获取应用在用户上的策略,返回用户信息和应用再组和单个用户策略列表
    :param email:
    :return:
    """
    user = User.query.filter_by(email=email).first_or_404()
    return jsonify([policy.export_data for policy in user.list_all_policies()])


@auth.route('/users/<string:email>/policy-action/', methods=['POST', 'DELETE'])
@basic_auth.login_required
def user_policy_action(email):
    """
    用户附加策略和解除策略.
    :param email:
    :return:
    """
    try:
        policy_id = request.get_json()['policy_id']
    except KeyError as e:
        raise ValidationError('Invalid: missing ' + e.args[0])
    user = User.query.filter_by(email=email).first_or_404()
    policy = Policy.query.get_or_404(policy_id)

    if request.method == 'POST':
        return jsonify([p.export_data() for p in user.attach_policy(policy)])
    elif request.method == 'DELETE':
        return jsonify([p.export_data() for p in user.detach_policy(policy)])
    else:
        return jsonify({}), 400


@auth.route('/users/token/', methods=['GET'])
@basic_auth.login_required
def get_token():
    """
    获取已登录用户的token
    :return:
    """
    if g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})


@auth.route('/groups/', methods=['GET'])
def get_groups():
    """
    获取所有组的列表
    :return:
    """
    groups = Group.query.all()
    return jsonify({'groups': [group.export_data() for group in groups]})


@auth.route('/groups/', methods=['POST'])
def new_group():
    """
    创建新的组
    :return:
    """
    group = Group()
    group.import_data(request.get_json())
    db.session.add(group)
    db.session.commit()
    return jsonify(group.export_data()), 201, {'Location': group.get_url()}


@auth.route('/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """
    按照group_id获取某个group
    :return:
    """
    return jsonify(Group.query.get_or_404(group_id).export_data())


@auth.route('/groups/<int:group_id>/users/')
def list_users_of_group(group_id):
    """
    列出某个组下的所有用户
    :param group_id:
    :return:
    """
    return jsonify([user.export_data() for user in Group.query.get_or_404(group_id).users])


@auth.route('/groups/add-user/', methods=['POST'])
def add_user_to_group():
    """
    向某个组中添加用户
    需要post中提供group_id,用户的email
    :return:
    """
    try:
        group_id = request.get_json()['group_id']
        email = request.get_json()['email']
    except KeyError as e:
        raise ValidationError('Invalid Group or User: missing ' + e.args[0])

    group = Group.query.get_or_404(group_id)
    user = User.query.filter_by(email=email).first_or_404()
    return jsonify([user.export_data() for user in group.add_user(user)])


@auth.route('/groups/remove-user/', methods=['POST'])
def remove_user_from_group():
    """
    把用户从组里移除
    需要post中提供group_id,用户的email
    :return:
    """
    try:
        group_id = request.get_json()['group_id']
        email = request.get_json()['email']
    except KeyError as e:
        raise ValidationError('Invalid Group or User: missing' + e.args[0])

    group = Group.query.get_or_404(group_id)
    user = User.query.filter_by(email=email).first_or_404()
    return jsonify([user.export_data() for user in group.remove_user(user)])


@auth.route('/policies/', methods=['GET'])
def get_policies():
    """
    获取所有策略的列表
    :return:
    """
    policies = Policy.query.filter(Policy.delete_date == '1000-01-01 00:00:00').all()
    return jsonify({'policies': [policy.export_data() for policy in policies]})


@auth.route('/policies/<string:policy_name>', methods=['GET'])
def get_policy(policy_name):
    """
    根据策略name获取策略
    :param policy_name:
    :return:
    """
    return jsonify(Policy.query.filter_by(name=policy_name).filter_by(
        delete_date='1000-01-01 00:00:00').first_or_404().export_data())


@auth.route('/policies/', methods=['POST'])
def new_policy():
    """
    新增一条策略
    :return:
    """
    policy = Policy()
    policy.import_data(request.get_json())
    db.session.add(policy)
    db.session.commit()
    return jsonify(policy.export_data()), 201, {'Location': policy.get_url()}


@auth.route('/policies/<string:policy_name>', methods=['PUT'])
def edit_policy(policy_name):
    """
    根据策略名称编辑指定的策略内容
    :param policy_name:
    :return:
    """
    policy = Policy.query.filter_by(name=policy_name).filter_by(delete_date='1000-01-01 00:00:00').first_or_404()
    policy.import_data(request.get_json())
    db.session.add(policy)
    db.session.commit()
    return jsonify(policy.export_data())


@auth.route('/policies/<string:policy_name>', methods=['DELETE'])
def delete_policy(policy_name):
    """
    根据策略名称标记删除指定的策略内容.
    :param policy_name:
    :return:
    """
    policy = Policy.query.filter_by(name=policy_name).filter_by(delete_date='1000-01-01 00:00:00').first_or_404()
    policy.delete_date = datetime.utcnow()
    db.session.add(policy)
    db.session.commit()
    return jsonify({})


@auth.route('/protected/')
@basic_auth.login_required
@admin_required()
def get_protected_resource():
    return jsonify({'resource': 1})
