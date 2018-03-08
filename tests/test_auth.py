# -*- coding: utf8 -*-
import unittest
import json
from werkzeug.exceptions import NotFound
from app import create_app, db
from .test_client import TestClient
from app.exceptions import ValidationError
from app.auth.models import User, Group
from flask import url_for


class TestAuthAPI(unittest.TestCase):
    default_email = "zhujinhe@vip.qq.com"
    default_username = 'dave'
    default_password = 'cat'
    default_group_name = 'group1'
    default_group_comments = 'group1 comments'

    def setUp(self):
        self.app = create_app('testing')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.drop_all()
        db.create_all()
        u = User(email=self.default_email,
                 username=self.default_username,
                 password=self.default_password)
        group = Group(name=self.default_group_name,
                      comments=self.default_group_comments)
        group.users.append(u)
        db.session.add(u)
        db.session.add(group)
        db.session.commit()
        # 默认使用token作为所有接口的验证方式
        self.client = TestClient(self.app, u.generate_auth_token(), '')

    def tearDown(self):
        db.session.remove()
        # db.drop_all()
        self.ctx.pop()

    def test_user_group(self):
        # 获取所有group
        rv, json_data = self.client.get(url_for('auth.get_groups'))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json_data['groups'][0]['name'], self.default_group_name)

        # 根据group_id获取group
        rv, json_data = self.client.get(url_for('auth.get_group', group_id=1))
        self.assertEqual(json_data['group_id'], 1)

        # 把用户添加到组
        u2 = User(email='bar@bar.com',
                  username='username_bar',
                  password='password_bar')
        db.session.add(u2)
        rv, json_data = self.client.post(url_for('auth.add_user_to_group'), data={'group_id': 1,
                                                                                  'email': 'bar@bar.com'})
        self.assertEqual(rv.status_code, 200)

        # 列出某个用户下所有的组
        rv, json_data = self.client.get(url_for('auth.get_groups_of_user', email=self.default_email))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]['group_id'], 1)

        # 列出某个组下所有的用户
        rv, json_data = self.client.get(url_for('auth.list_users_of_group', group_id=1))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(json_data), 2)

        # 把用户移出组
        rv, json_data = self.client.post(url_for('auth.remove_user_from_group'), data={'group_id': 1,
                                                                                       'email': self.default_email})
        self.assertEqual(rv.status_code, 200)
        rv, json_data = self.client.get(url_for('auth.list_users_of_group', group_id=1))
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]['email'], 'bar@bar.com')

    def test_user_credential(self):
        # 默认是以token的认证方式, 在setUp中定义的.
        rv, json_data = self.client.get(url_for('auth.get_user_by_email', email=self.default_email))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json_data['username'], self.default_username)

        # 测试以账号密码的方式认证
        self.client = TestClient(self.app, self.default_email, self.default_password)
        rv, json_data = self.client.get(url_for('auth.get_user_by_email', email=self.default_email))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json_data['username'], self.default_username)

        # 测试获取token, 并检查是否生效
        rv, json_data = self.client.get(url_for('auth.get_token'))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(User.verify_auth_token(json_data['token']).email, self.default_email)

        # 错误的账号密码
        self.client = TestClient(self.app, self.default_email, '%s_invalid' % self.default_password)
        rv, json_data = self.client.get(url_for('auth.get_user_by_email', email=self.default_email))
        self.assertEqual(rv.status_code, 401)

    def test_user_policies(self):
        # add new policy, new policy version and set as default.
        policy_document = {"Version": "1", "Statement": [{"Action": ["oss:List*", "oss:Get*"], "Effect": "Allow",
                                                          "Resource": ["acs:oss:*:*:samplebucket",
                                                                       "acs:oss:*:*:samplebucket/*"],
                                                          "Condition": {"IpAddress": {"acs:SourceIp": "42.160.1.0"}}}]}

        rv, json_data = self.client.post(url_for('auth.get_policies'), data={'name': 'foo',
                                                                             'description': 'foo desc',
                                                                             'is_new_version': True,
                                                                             'document': json.dumps(policy_document),
                                                                             'set_as_default': True})
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv.headers['Location'], url_for('auth.get_policy', policy_name='foo'))
        rv, json_data = self.client.get(url_for('auth.get_policy', policy_name='foo'))
        self.assertIsNone(json_data['update_date'])

        # 获取策略列表
        rv, json_data = self.client.get(url_for('auth.get_policies'))
        self.assertEqual(rv.status_code, 200)

        # 获取某个策略
        rv, json_data = self.client.get(url_for('auth.get_policy', policy_name='foo'))
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(json_data['name'] == 'foo')

        # 测试错误的策略格式
        policy_document_invalid = {'foo': 'bar'}
        with self.assertRaisesRegexp(ValidationError, 'JSON ValidationError: '):
            rv, json_data = self.client.post(url_for('auth.get_policies'),
                                             data={'name': 'foo',
                                                   'description': 'foo desc',
                                                   'is_new_version': True,
                                                   'document': json.dumps(policy_document_invalid),
                                                   'set_as_default': True})

        # 编辑策略
        rv, json_data = self.client.put(url_for('auth.get_policy', policy_name='foo'),
                                        data={'name': 'foo',
                                              'description': 'new foo desc',
                                              'is_new_version': False})
        self.assertEqual(rv.status_code, 200)
        self.assertRegexpMatches(json_data['description'], 'new foo desc')
        self.assertIsNotNone(json_data['update_date'])

        # 获取所有策略版本
        rv, json_data = self.client.get(url_for('auth.get_policy_versions', policy_name='foo'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNotNone(json_data['versions'][0]['document'])

        # 获取某个指定version的version详情
        rv, json_data = self.client.get(url_for('auth.get_policy_version', version_id=1))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json_data['policy_id'], 1)
        self.assertEqual(json_data['version_id'], 1)

        # 新增某个指定version的version详情
        rv, json_data = self.client.post(url_for('auth.get_policy_version', version_id=1),
                                         data={'policy_id': 1,
                                               'document': json.dumps(policy_document)})
        self.assertEqual(rv.status_code, 201)
        self.assertEqual(rv.headers['Location'], url_for('auth.get_policy_version', version_id=2))

        # 修改某个指定version的version详情
        policy_document['Version'] = "2"
        rv, json_data = self.client.put(url_for('auth.get_policy_version', version_id=2),
                                        data={'policy_id': 1,
                                              'document': json.dumps(policy_document)})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(json_data['document'])['Version'], "2")

        # 列出某个用户下的所有策略
        rv, json_data = self.client.get(url_for('auth.get_policies_of_user', email=self.default_email))
        self.assertEqual(rv.status_code, 200)
        self.assertListEqual(json_data, [])

        # 放在最后:
        # 标记删除策略, 策略被标记删除, 版本也被标记删除
        rv, json_data = self.client.delete(url_for('auth.get_policy', policy_name='foo'))
        self.assertEqual(rv.status_code, 200)
        with self.assertRaises(NotFound):
            rv, json_data = self.client.get(url_for('auth.get_policy', policy_name='foo'))
        with self.assertRaises(NotFound):
            rv, json_data = self.client.get(url_for('auth.get_policy_versions', policy_name='foo'))
