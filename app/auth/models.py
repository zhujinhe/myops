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
        policies = [g.policies.all() for g in User.query.get(self.user_id).groups]
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
    某条策略.
        "Policy": {
        "PolicyName": "OSS-Administrator",
        "Description": "OSS管理员权限",
        "DefaultVersion": "v1",
        "CreateDate": "2015-01-23T12:33:18Z",
        "UpdateDate": "2015-01-23T12:33:18Z",
    }
    Policy与PolicyVersion是一对多.
    """
    # TODO 同时记录Policy和PolicyVersion有些过度设计,可以简化为只要Policy并记录log的方式.

    __tablename__ = 'policies'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}
    policy_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    description = db.Column(db.String(1024))
    default_version = db.Column(db.Integer)
    versions = db.relationship('PolicyVersion', backref='policy', lazy='dynamic')
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_date = db.Column(db.DateTime)
    delete_date = db.Column(db.DateTime, default='1000-01-01 00:00:00')

    def get_url(self):
        return url_for('auth.get_policy', policy_name=self.name, _external=True)

    def set_default_version(self, version_id):
        version = self.versions.get(version_id).first()
        if version is None:
            return False
        self.default_version = version.version_id
        db.session.add(self)
        return True

    @property
    def default_document(self):
        default_version = self.versions.filter_by(version_id=self.default_version).first()
        if default_version is not None:
            return default_version.document

    def add_policy_version(self, document, set_as_default=False):

        new_version = PolicyVersion(
            policy_id=self.policy_id,
            document=document,
        )
        new_version = new_version.import_data({'policy_id': self.policy_id,
                                               'document': document})

        db.session.add(new_version)
        db.session.flush()

        if set_as_default:
            self.default_version = new_version.version_id
        self.versions.append(new_version)
        db.session.add(self)
        return new_version

    def export_data(self):
        """
         返回结果
        :return:
        """
        return {
            'policy_id': self.policy_id,
            'name': self.name,
            'description': self.description,
            'versions': [version.export_data() for version in self.versions],
            'default_document': self.default_document,
            'create_date': self.create_date,
            'update_date': self.update_date
        }

    def import_data(self, data):
        """
        导入内容, 必须参数验证, 参数正确性验证, 其他验证都在这里做认证.

        :param data:
        :return:
        """
        try:
            self.name = data['name']
            is_new_version = data['is_new_version']
        except KeyError as e:
            raise ValidationError('Invalid Policy: missing ' + e.args[0])
        self.description = data.get('description')

        if is_new_version is True:
            try:
                set_as_default = data['set_as_default']
                document = data['document']
            except KeyError as e:
                raise ValidationError('Invalid Policy: missing ' + e.args[0] + ' for new version')
            self.add_policy_version(document=document, set_as_default=set_as_default)
        else:
            self.update_date = datetime.utcnow()
        return self

    def __repr__(self):
        return '<Policy %r>' % self.name


class PolicyVersion(db.Model):
    """
    策略内容和版本号
        "PolicyVersion": {
        "VersionId": "v3",
        "IsDefaultVersion": false,
        "CreateDate": "2015-01-23T12:33:18Z",
        "PolicyDocument": "{ \"Statement\": [{ \"Action\": [\"oss:*\"], \"Effect\": \"Allow\", \"Resource\": [\"acs:oss:*:*:*\"]}], \"Version\": \"1\"}"
    }
    """
    __tablename__ = 'policy_versions'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    version_id = db.Column(db.Integer, primary_key=True)
    policy_id = db.Column(db.Integer, db.ForeignKey('policies.policy_id'))
    document = db.Column(db.JSON)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    delete_date = db.Column(db.DateTime, default='1000-01-01 00:00:00')

    def get_url(self):
        return url_for('auth.get_policy_version', version_id=self.version_id, _external=True)

    @property
    def is_default(self):
        return self.version_id == self.policy.default_version

    def validate_document(self, json_schema=None):
        if not json_schema:
            return json_schema_validator_by_filename(self.document, 'auth_policy.json')
        else:
            return json_schema_validator(self.document, json_schema)

    def export_data(self):
        return {
            'version_id': self.version_id,
            'document': self.document,
            'create_date': self.create_date,
            'policy_id': self.policy_id,
            'is_default': self.is_default
        }

    def import_data(self, data):
        try:
            self.policy_id = data['policy_id']
            self.document = data['document']
        except KeyError as e:
            raise ValidationError('Invalid PolicyVersion: missing ' + e.args[0])

        # 验证document的合法性.
        if not self.validate_document():
            raise ValidationError('Invalid PolicyVersion: document validation error')

        return self

    def __repr__(self):
        return '<PolicyVersion %r>' % self.version_id
