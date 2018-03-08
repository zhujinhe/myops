# -*- coding: utf8 -*-
import json

# flask
from flask import request, jsonify
from . import action
from app.auth.views import basic_auth
from app.utils.json_schema import json_schema_validator_by_filename

# taskflow
import taskflow.engines
from app.utils.taskflow_utils import get_taskflow_backend

# ops
from app.utils.taskflow_utils.flows import flow_init_server_ops_api

# debug
import logging
logging.basicConfig(level=logging.DEBUG)


@action.route('/init_server_ops_api', methods=['POST'])
@basic_auth.login_required
def init_server_ops_api():
    # TODO 增加结果输出
    store = request.get_json()
    json_schema_validator_by_filename(store, 'action_init_api_store.json')
    wf = flow_init_server_ops_api()
    engine = taskflow.engines.load(wf, store=store, backend=get_taskflow_backend())
    engine.run()
    return jsonify({})
