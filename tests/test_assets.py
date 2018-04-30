# -*- coding: utf8 -*-
import unittest
import json
from app import create_app, db
from .test_client import TestClient
from app.exceptions import ValidationError
from app.auth.models import User, Group
from app.assets.models import Server
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
        # 默认使用token作为所有接口的验证方式
        self.client = TestClient(self.app, u.generate_auth_token(), '')

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.ctx.pop()

    def test_server(self):
        self.assertIsNotNone(Server.query.all())
        rv, json_data = self.client.get(url_for('assets.get_servers'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNotNone(json_data)
