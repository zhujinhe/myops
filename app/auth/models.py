# -*- coding: utf8 -*-
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, url_for
from ..exceptions import ValidationError
from app.utils.json_schema import json_schema_validator, json_schema_validator_by_filename

# RAM-User和RAM-Group是many-to-many
user_group_relationships = db.Table('user_group_relationships',
                                    db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), nullable=False),
                                    db.Column('group_id', db.Integer, db.ForeignKey('groups.group_id'), nullable=False),
                                    db.PrimaryKeyConstraint('user_id', 'group_id')
                                    )

# 用户与策略引用是many-to-many
user_policy_attachments = db.Table('user_policy_attachments',
                                   db.Column('user_id', db.Integer, db.ForeignKey('users.user_id'), nullable=False),
                                   db.Column('policy_id', db.Integer, db.ForeignKey('policies.policy_id'),
                                             nullable=False),
                                   db.Column('create_date', db.DateTime, default=datetime.utcnow),
                                   db.PrimaryKeyConstraint('user_id', 'policy_id')
                                   )

# 组与与策略引用是many-to-many
group_policy_attachments = db.Table('group_policy_attachments',
                                    db.Column('group_id', db.Integer, db.ForeignKey('groups.group_id'), nullable=False),
                                    db.Column('policy_id', db.Integer, db.ForeignKey('policies.policy_id'),
                                              nullable=False),
                                    db.Column('create_date', db.DateTime, default=datetime.utcnow),
                                    db.PrimaryKeyConstraint('group_id', 'policy_id')
                                    )


class User(db.Model):
    """
    RAM-USER是一种实体身份, 有ID和密码, 通常和某个确定的人或程序一一对应.
    """
    __tablename__ = 'users'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(64))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(1024))
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_date = db.Column(db.DateTime)
    groups = db.relationship('Group',
                             secondary=user_group_relationships,
                             backref=db.backref('users', lazy='dynamic'),
                             lazy='dynamic')
    policies = db.relationship('Policy',
                               secondary=user_policy_attachments,
                               backref=db.backref('users', lazy='dynamic'),
                               lazy='dynamic')

    def get_id(self):
        try:
            return str(self.user_id)
        except AttributeError:
            raise NotImplementedError('No `user_id` attribute - override `get_id`')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'user_id': self.user_id}).decode('ascii')

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['user_id'])

    def list_groups(self):
        return self.groups

    def attach_policy(self, policy):
        if isinstance(policy, Policy):
            self.policies.append(policy)
            db.session.add(self)
            return self.policies

    def detach_policy(self, policy):
        if isinstance(policy, Policy):
            self.policies.remove(policy)
            db.session.add(self)
            return self.policies

    def list_user_policies(self):
        """
        返回默认应用到用户上的策略和应用到用户所在组上的策略.
        :return:
        """
        return self.policies.all()

    def list_group_policies(self):
        """
        应用到用户所在组的策略.返回的是策略的列表
        :return:
        """
        # TODO: 不知道怎么用ORM写出来了,暂时这么写吧.
        policies = [g.policies.all() for g in self.groups]
        return list(set([p for j in policies for p in j]))

    def list_all_policies(self):
        """
        应用到用户和用户所在所有组的策略的集合.
        :return:
        SQL:
        select * from policies where policy_id in (select policy_id from user_policy_attachments where user_id = 1 ) or
        policy_id in (select policy_id from group_policy_attachments where group_id in (select group_id from user_group_relationships where user_id = 1) );
        """
        policies = self.list_group_policies()
        policies.extend(self.list_user_policies())
        return list(set([p for p in policies]))

    def export_data(self):
        return {'user_id': self.user_id,
                'email': self.email,
                'username': self.username,
                'group_id': self.group_id,
                'description': self.description,
                'create_date': self.create_date}

    def __repr__(self):
        return '<User %r>' % self.username


class Group(db.Model):
    """
    RAM-Group是一种虚拟身份,有ID没密码,需要与某个实体关联后才能被使用.
    """
    __tablename__ = 'groups'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}
    group_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    comments = db.Column(db.String(1024))
    policies = db.relationship('Policy',
                               secondary=group_policy_attachments,
                               backref=db.backref('groups', lazy='dynamic'),
                               lazy='dynamic')

    def get_url(self):
        return url_for('auth.get_group', group_id=self.group_id, _external=True)

    def add_user(self, user):
        """
        返回所有users
        :param user:
        :return:
        """
        if isinstance(user, User):
            self.users.append(user)
            db.session.add(self)
            return self.users

    def remove_user(self, user):
        """
        返回所有users
        :param user:
        :return:
        """
        if isinstance(user, User):
            self.users.remove(user)
            db.session.add(self)
            return self.users

    def list_users(self):
        return self.users

    def export_data(self):
        return {'group_id': self.group_id,
                'name': self.name,
                'comments': self.comments}

    def import_data(self, data):
        try:
            self.name = data['name']
        except KeyError as e:
            raise ValidationError('Invalid Group: missing ' + e.args[0])
        return self

    def __repr__(self):
        return '<Group %r>' % self.name


class Policy(db.Model):
    """
    策略内容
    """

    __tablename__ = 'policies'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}
    policy_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    description = db.Column(db.String(1024))
    document = db.Column(db.JSON, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_date = db.Column(db.DateTime)
    delete_date = db.Column(db.DateTime, default='1000-01-01 00:00:00')

    def get_url(self):
        return url_for('auth.get_policy', policy_name=self.name, _external=True)

    def validate_document(self, json_schema=None):
        if not json_schema:
            return json_schema_validator_by_filename(self.document, 'auth_policy.json')
        else:
            return json_schema_validator(self.document, json_schema)

    def export_data(self):
        """
         返回结果
        :return:
        """
        if self.delete_date is not '1000-01-01 00:00:00':
            return {
                'policy_id': self.policy_id,
                'name': self.name,
                'description': self.description,
                'document': self.document,
                'create_date': self.create_date,
                'update_date': self.update_date
            }
        else:
            return {}

    def import_data(self, data):
        """
        导入内容, 必须参数验证, 参数正确性验证, 其他验证都在这里做认证.

        :param data:
        :return:
        """
        try:
            self.name = data['name']
            self.document = data['document']
        except KeyError as e:
            raise ValidationError('Invalid Policy: missing ' + e.args[0])
        # 验证document的合法性.
        if not self.validate_document():
            raise ValidationError('Invalid Policy: document validation error')
        self.description = data.get('description')
        self.update_date = datetime.utcnow()

        return self

    def __repr__(self):
        return '<Policy %r>' % self.name
