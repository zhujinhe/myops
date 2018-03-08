# -*- coding: utf8 -*-
import unittest
import json
from werkzeug.exceptions import NotFound
from app import create_app, db
from .test_client import TestClient
from app.exceptions import ValidationError
from app.auth.models import User, Group
from app.assets.models import Server, LoadBalancer, LoadBalancerListener
from flask import url_for


class TestAssetsAPI(unittest.TestCase):
    default_email = "zhujinhe@vip.qq.com"
    default_username = 'dave'
    default_password = 'cat'

    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        u = User(email=self.default_email,
                 username=self.default_username,
                 password=self.default_password)
        db.session.add(u)
        db.session.commit()
        # 从阿里云初始化信息
        Server.update_by_id()
        LoadBalancer.update_by_id(update_listener=True)
        # 默认使用token作为所有接口的验证方式
        self.client = TestClient(self.app, u.generate_auth_token(), '')

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.ctx.pop()

    def test_server(self):
        # 从阿里云中导入数据到本地数据库.
        self.assertIsNotNone(Server.query.all())
        rv, json_data = self.client.get(url_for('assets.get_servers'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNotNone(json_data)

    def test_loadbalancer(self):
        # LoadBalancer的检查
        self.assertIsNotNone(LoadBalancer.query.all())
        rv, json_data = self.client.get(url_for('assets.get_loadbalancers'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNotNone(json_data)
        # LoadBalancerListener的检查
        self.assertIsNotNone(LoadBalancerListener.query.all())

    def test_pillar(self):
        minion_id = 'OPS-APP-API11'
        pillar_dict = {"pillar_foo": "pillar_bar", "pillar_baz": {"baz_k": 1}}
        s = Server.query.filter_by(minion_id=minion_id).first()
        if s is not None:
            s.add_pillar(pillar_dict)
        rv, json_data = self.client.get(url_for('assets.get_pillars', minion_id=minion_id))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json_data, pillar_dict)
