# -*- coding: utf8 -*-
from flask import request, jsonify
from app.utils.json_schema import json_schema_validator_by_filename
from app.auth.decorators import permission_required
from app.auth.views import basic_auth
from . import assets
from .models import Server, LoadBalancer, Salt
import json


@assets.route('/')
def index():
    return jsonify({'message': 'assets.index'})


@assets.route('/servers/', methods=['GET'])
# @permission_required(action='foo', resource='bar')
def get_servers():
    """
    列出所有的服务器资源
    :return:
    """
    return jsonify([server.export_data() for server in Server.query.all()])


@assets.route('/servers/<string:instance_id>/', methods=['GET'])
def get_server_by_instance_id(instance_id):
    return jsonify(Server.query.filter_by(instance_id=instance_id).first_or_404().export_data())


@assets.route('/servers/<int:id>/', methods=['GET'])
def get_server(id):
    return jsonify(Server.query.get_or_404(id).export_data())


@assets.route('/loadbalancers/', methods=['GET'])
def get_loadbalancers():
    return jsonify([loadbalancer.export_data() for loadbalancer in LoadBalancer.query.all()])


@assets.route('/salt/<string:minion_id>/pillars/')
@basic_auth.login_required
def get_pillars(minion_id):
    salt = Salt.query.filter_by(minion_id=minion_id).first()
    if salt and salt.pillar:
        return jsonify(json.loads(salt.pillar))
    return jsonify({})


@assets.route('/servers/<string:instance_id>/salt/pillars/', methods=['GET'])
@basic_auth.login_required
def get_server_pillars(instance_id):
    server = Server.query.filter_by(instance_id=instance_id).first()
    if server and server.minion and server.minion.pillar:
        return jsonify(json.loads(server.minion.pillar))
    return jsonify({})


@assets.route('/servers/<string:instance_id>/salt/states/', methods=['GET'])
@basic_auth.login_required
def get_server_top_states(instance_id):
    server = Server.query.filter_by(instance_id=instance_id).first()
    if server and server.minion:
        return server.minion.get_state()
    return ""

@assets.route('/servers/<string:instance_id>/salt/jobs/<int:jid>')
@basic_auth.login_required
def get_server_jobs(instance_id, jid):
    server = Server.query.filter_by(instance_id=instance_id).first()
    if server and server.minion:
        return jsonify(server.lookup_jid(jid).json())


@assets.route('/servers/<string:instance_id>/salt/local/', methods=['POST'])
@basic_auth.login_required
def server_salt_local(instance_id):
    # TODO 权限认证
    post_data = request.get_json()
    # TODO 现在只做了粗略格式验证
    json_schema_validator_by_filename(post_data, 'assets_salt_local.json')
    server = Server.query.filter_by(instance_id=instance_id).first()
    if server and server.minion:
        ret = server.minion.local(post_data['func'], arg=post_data.get('args', []), kwarg=post_data.get('kwargs', {}))
        return jsonify(ret.json())
    return jsonify({})
