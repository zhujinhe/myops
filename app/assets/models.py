# -*- coding: utf8 -*-
from copy import deepcopy
from flask import current_app
from app import db
from app.models import ServerMacro
from app.utils import get_aliyun_client, get_aliyun_ecs, get_aliyun_slb, YunTongXunClient, SaltNetAPIClient
from app.utils.aliyun_utils import get_aliyun_ecs_by_instance_id, get_aliyun_slb_by_loadbalancer_id, \
    get_aliyun_slb_listeners_by_loadbalancer_id
from app.utils.dictupdate import dict_merge
from config import Config
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkslb.request.v20140515 import SetListenerAccessControlStatusRequest, \
    AddListenerWhiteListItemRequest, RemoveListenerWhiteListItemRequest, \
    AddBackendServersRequest
import json
from app.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError


# 资源信息,
class Server(db.Model):
    """
    资产管理,服务器.
    服务器信息保存在数据库中, 并支持在如阿里云平台中导入更新.
    """
    __tablename__ = 'servers'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64), default='', nullable=False)
    description = db.Column(db.String(128))
    memory = db.Column(db.Integer)
    cpu = db.Column(db.Integer)
    status = db.Column(db.String(64))
    inner_ip_address = db.Column(db.String(64))
    public_ip_address = db.Column(db.String(64))
    server_type = db.Column(db.String(64))
    region_id = db.Column(db.String(64))
    minion = db.relationship('Salt', backref='server', uselist=False)
    macros = db.relationship('ServerMacro', backref='servers', lazy='dynamic')

    @staticmethod
    def _update(instance_id, instance):
        """
        从ECS中拉取单个服务器信息
        :param instance_id: 实例id
        :param instance: 从ECS返回的实例
        :return:
        """
        from sqlalchemy.exc import IntegrityError

        server = Server.query.filter_by(instance_id=instance_id).first() or Server()
        server.instance_id = instance['InstanceId']
        server.name = instance['InstanceName']
        server.cpu = instance['Cpu']
        server.memory = instance['Memory']
        server.status = instance['Status']
        server.inner_ip_address = instance['InnerIpAddress']['IpAddress'][0]
        server.public_ip_address = instance['PublicIpAddress']['IpAddress'][0]
        server.region_id = instance['RegionId']
        server.server_type = 'Aliyun_ESC'
        db.session.add(server)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return server

    @staticmethod
    def update_by_id(instance_id=None):
        """
        从阿里云的接口中获取信息,并按照instance_id进行信息的更新.
        如果未定义instance_id, 则更新所有记录.
        :return:
        """
        ret = []
        for region in Config.aliyun_region:
            for instance in get_aliyun_ecs(region):
                if instance_id is None:
                    ret.append(Server._update(instance['InstanceId'], instance))
                elif instance_id == instance['InstanceId']:
                    ret.append(Server._update(instance_id, instance))
        return ret

    def update_salt(self):
        if not self.minion:
            self.minion = Salt(instance_id=self.instance_id)
            db.session.add(self)
            db.session.commit()
        self.minion.update()

    def update(self, update_salt=False):
        if update_salt:
            self.update_salt()
        return Server.update_by_id(self.instance_id)

    def add_yuntongxun_white_list(self):
        yuntongxun_client = YunTongXunClient(Config.yuntongxun_username, Config.yuntongxun_password)
        return yuntongxun_client.add_ips(str(self.public_ip_address))

    def local(self, func, *args, **kwargs):
        self.update_salt()
        return self.minion.local(func, *args, **kwargs)

    def local_async(self, func, *args, **kwargs):
        self.update_salt()
        return self.minion.local_async(func, *args, **kwargs)

    def lookup_jid(self, jid):
        """
        默认登录用户能查所有的jobs, 这里设置只能返回本服务器的jobs.
        这里用了一个requests的内部变量做的修改.
        :param jid:
        :return:
        """
        self.update_salt()
        ret = self.minion.lookup_jid(jid)
        ret._content = json.dumps({
            'return': [job_info for job_info in ret.json()['return'] if self.minion.minion_id in job_info]
        })
        return ret

    def salt_key_accept(self):
        """
        设置master接受minion_id的key, 如果没有salt minion_id, 默认用实例别名
        :return:
        """
        self.update_salt()
        return Salt.accept_key(self.minion.minion_id)

    def add_pillar(self, pillar_dict, **kwargs):
        """
        增加pillar
        :param pillar_dict: 要增加的pillar字典.
        :param kwargs: recursive_update=True, merge_lists=False
        :return:
        """
        return self.minion.add_pillar(pillar_dict, **kwargs)

    def export_data(self):
        return {'id': self.id,
                'instance_id': self.instance_id,
                'name': self.name,
                'description': self.description,
                'memory': self.memory,
                'cpu': self.cpu,
                'status': self.status,
                'inner_ip_address': self.inner_ip_address,
                'public_ip_address': self.public_ip_address,
                'server_type': self.server_type,
                'region_id': self.region_id
                }

    def __repr__(self):
        return '<Server %r>' % self.name


class LoadBalancer(db.Model):
    """
    负载均衡设备的信息, 与LoadBalancerListener是一对多的关系.
    """
    __tablename__ = 'loadbalancers'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    id = db.Column(db.Integer, primary_key=True)
    loadbalancer_id = db.Column(db.String(64), unique=True, nullable=False)
    loadbalancer_name = db.Column(db.String(64))
    address = db.Column(db.String(64))
    address_type = db.Column(db.String(64))
    loadbalancer_status = db.Column(db.String(64))
    region_id = db.Column(db.String(64))
    listeners = db.relationship('LoadBalancerListener', backref='loadbalancer', lazy='dynamic')

    @staticmethod
    def _update(loadbalancer_id, ali_loadbalancer):
        """
        从ECS中拉取单个SLB信息
        :param loadbalancer_id: 实例id
        :param ali_loadbalancer: 从SLB返回的实例
        :return:
        """
        from sqlalchemy.exc import IntegrityError
        loadbalancer = LoadBalancer.query.filter_by(loadbalancer_id=loadbalancer_id).first() or LoadBalancer()
        loadbalancer.loadbalancer_id = ali_loadbalancer['LoadBalancerId']
        loadbalancer.loadbalancer_name = ali_loadbalancer.get('LoadBalancerName', '')
        loadbalancer.address = ali_loadbalancer['Address']
        loadbalancer.address_type = ali_loadbalancer['AddressType']
        loadbalancer.loadbalancer_status = ali_loadbalancer['LoadBalancerStatus']
        loadbalancer.region_id = ali_loadbalancer['RegionId']
        db.session.add(loadbalancer)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return loadbalancer

    @staticmethod
    def _update_listeners(loadbalancer_id):
        """
        更新listener
        :return:
        """
        # 获取listener的混合属性.
        listeners = get_aliyun_slb_listeners_by_loadbalancer_id(loadbalancer_id)
        ret = []

        for ali_listener in listeners:
            # 在数据库中搜索, 有就更新, 没有就新增
            listener = LoadBalancerListener.query.filter(
                LoadBalancerListener.listener_port == ali_listener[1],
                LoadBalancerListener.listener_protocol == ali_listener[0],
                LoadBalancerListener.loadbalancer_id == loadbalancer_id
            ).first() or LoadBalancerListener()
            #
            listener.loadbalancer_id = loadbalancer_id
            listener.listener_port = ali_listener[1]
            listener.listener_protocol = ali_listener[0]
            listener.status = ali_listener[2]['Status']
            listener.backend_server_port = ali_listener[2]['BackendServerPort']
            db.session.add(listener)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
            ret.append(listener)
        return ret

    @staticmethod
    def update_by_id(loadbalancer_id=None, update_listener=False):
        """
        从阿里云的接口中获取信息,并按照loadbalancer_id进行信息的更新.
        如果未定义loadbalancer, 则更新所有记录.
        :return:
        """
        ret = []
        for region in Config.aliyun_region:
            for loadbalancer in get_aliyun_slb(region):
                if loadbalancer_id is None:
                    ret.append(LoadBalancer._update(loadbalancer['LoadBalancerId'], loadbalancer))
                    if update_listener:
                        LoadBalancer._update_listeners(loadbalancer['LoadBalancerId'])
                elif loadbalancer_id == loadbalancer['LoadBalancerId']:
                    ret.append(LoadBalancer._update(loadbalancer_id, loadbalancer))
                    if update_listener:
                        LoadBalancer._update_listeners(loadbalancer_id)
        return ret

    def update(self, update_listener=False):
        return LoadBalancer.update_by_id(self.loadbalancer_id, update_listener=update_listener)

    def update_listeners(self):
        return LoadBalancer._update_listeners(self.loadbalancer_id)

    def add_backend_servers(self, servers):
        """
        添加后端服务器, 默认的权重是100
        :param servers: ['i-bp15ikd9yfa7iu91xn2t'] 服务器的instance_id列表
        :return:
        """
        if not isinstance(servers, list):
            servers = [servers]
        aliyun_client = get_aliyun_client(readonly=False)
        aliyun_request = AddBackendServersRequest.AddBackendServersRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_LoadBalancerId(self.loadbalancer_id)
        aliyun_request.set_BackendServers(
            json.dumps([{"ServerId": server, "Weight": "100"} for server in servers]))
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        return json.loads(aliyun_response)

    def get_attribute(self):
        """
        从阿里云获取某个slb的信息
        :return:
        """
        try:
            return get_aliyun_slb_by_loadbalancer_id(self.loadbalancer_id)
        except ServerException:
            return None

    def export_data(self):
        return {'id': self.id,
                'loadbalancer_id': self.loadbalancer_id,
                'loadbalancer_name': self.loadbalancer_name,
                'address': self.address,
                'address_type': self.address_type,
                'loadbalancer_status': self.loadbalancer_status,
                'region_id': self.region_id,
                'listeners': [listener.export_data() for listener in self.listeners]}

    def __repr__(self):
        return '<LoadBalancer %r>' % self.loadbalancer_id


class LoadBalancerListener(db.Model):
    """
    负载均衡上配置的监听端口的信息. 只记录用得到的信息.
    """
    __tablename__ = 'loadbalancer_listeners'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    id = db.Column(db.Integer, primary_key=True)
    listener_port = db.Column(db.Integer, nullable=False)
    listener_protocol = db.Column(db.String(64))
    backend_server_port = db.Column(db.Integer)
    status = db.Column(db.String(64))
    loadbalancer_id = db.Column(db.String(64), db.ForeignKey('loadbalancers.loadbalancer_id'))

    @staticmethod
    def update_by_loadbalancer_id(loadbalancer_id=None):
        """
        :param loadbalancer_id:
        :return:
        """
        ret = []

        if loadbalancer_id is None:
            loadbalancers = LoadBalancer.query.all()
        else:
            loadbalancers = LoadBalancer.query.filter_by(loadbalancer_id=loadbalancer_id).first()

        for loadbalancer in loadbalancers:
            ret.append(loadbalancer.update_listeners())
        return ret

    def set_listener_access_control_status(self, status='open_white_list'):
        """
        设置某个端口的白名单开关
        :param status: 取值：open_white_list | close
        :return:
        """
        aliyun_client = get_aliyun_client(readonly=False)
        aliyun_request = SetListenerAccessControlStatusRequest.SetListenerAccessControlStatusRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_LoadBalancerId(self.loadbalancer_id)
        aliyun_request.set_ListenerPort(self.listener_port)
        aliyun_request.set_AccessControlStatus(status)
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)

        return json.loads(aliyun_response)

    def add_white_list_items(self, ip_source_items):
        """
        端口白名单中增加IP或者以逗号为分隔符的IP列表
        :param ip_source_items: 支持ip地址或ip地址段的输入，多个ip地址或ip地址段间用”,”分割。不支持传入0.0.0.0类似的地址
        :return:
        """
        aliyun_client = get_aliyun_client(readonly=False)
        aliyun_request = AddListenerWhiteListItemRequest.AddListenerWhiteListItemRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_LoadBalancerId(self.loadbalancer_id)
        aliyun_request.set_ListenerPort(self.listener_port)
        aliyun_request.set_SourceItems(ip_source_items)
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        return json.loads(aliyun_response)

    def remove_white_list_items(self, ip_source_items):
        """
        端口白名单中删除IP或者以逗号为分隔符的IP列表.
        如在AccessControlStatus为open_white_list时，把所有ip都Remove了，则会访问不通
        :param ip_source_items: 支持ip地址或ip地址段的输入，多个ip地址或ip地址段间用”,”分割。
        :return:
        """
        aliyun_client = get_aliyun_client(readonly=False)
        aliyun_request = RemoveListenerWhiteListItemRequest.RemoveListenerWhiteListItemRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_LoadBalancerId(self.loadbalancer_id)
        aliyun_request.set_ListenerPort(self.listener_port)
        aliyun_request.set_SourceItems(ip_source_items)
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        return json.loads(aliyun_response)

    def export_data(self):
        return {'id': self.id,
                'listener_port': self.listener_port,
                'listener_protocol': self.listener_protocol,
                'backend_server_port': self.backend_server_port,
                'status': self.status,
                'loadbalancer_id': self.loadbalancer_id}

    def __repr__(self):
        return '<LoadBalancerListener %r>' % self.listener_port


class Salt(db.Model):
    """
    存放salt minion的相关信息.与服务器为一对一.
    pillar只保留最新的一份json格式.
    state配合master_tops动态生成state的top.sls
    """
    __tablename__ = 'salt'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.String(64), db.ForeignKey('servers.instance_id'), unique=True, nullable=False)
    minion_id = db.Column(db.String(64))
    pillar = db.Column(db.JSON)
    state = db.Column(db.String(256))
    key_accepted = db.Column(db.Integer)

    salt_client = SaltNetAPIClient(Config.salt_url, username=Config.salt_pam_username,
                                   password=Config.salt_pam_password,
                                   eauth='pam')
    logged_in = False

    def __init__(self, *args, **kwargs):
        self.salt_client.auth()
        self.logged_in = True
        super(Salt, self).__init__(*args, **kwargs)

    def _login(self):
        if not self.logged_in:
            self.salt_client.auth()
            self.logged_in = True

    def _local(self, tgt, func, *args, **kwargs):
        self._login()
        ret = self.salt_client.local(tgt, func, *args, **kwargs)
        if ret.status_code == 401:
            raise ValidationError('SaltStack NetAPI Permission required')
        return ret

    def _local_async(self, tgt, func, *args, **kwargs):
        self._login()
        ret = self.salt_client.local_async(tgt, func, *args, **kwargs)
        if ret.status_code == 401:
            raise ValidationError('SaltStack NetAPI Permission required')
        return ret

    def _get_minion_id(self):
        return self._local('G@ip_interfaces:eth0:{0} or G@ip_interfaces:eth1:{0}'.format(self.server.public_ip_address),
                           'grains.item', expr_form='compound')

    def update_minion_id(self, minion_id=None):
        """
        优先级: 手工指定 > salt中通过IP筛选的minion_id > 阿里云中的主机名
        :param minion_id:
        :return:
        """
        if minion_id:
            self.minion_id = minion_id
        else:
            # 根据IP地址获取当前的已认证的客户端minion_id, 如果获取不到, 则用Server.name
            minion_ids = self._get_minion_id().json().get('return', [{}])[0].keys()
            if len(minion_ids) > 0:
                self.minion_id = minion_ids[0]
            else:
                self.minion_id = self.server.name
        db.session.add(self)
        db.session.commit()
        return self.minion_id

    def update(self):
        self.update_minion_id()
        if not self.key_accepted:
            Salt.accept_key(self.minion_id)
        return True

    def local(self, func, *args, **kwargs):
        return self._local(self.minion_id, func, *args, **kwargs)

    def local_async(self, func, *args, **kwargs):
        return self._local_async(self.minion_id, func, *args, **kwargs)

    @staticmethod
    def lookup_jid(jid):
        """
        默认登录用户能查所有的jobs, 这里设置只能返回本服务器的jobs.
        这里用了一个requests的内部变量做的修改.
        :param jid:
        :return:
        """
        ret = Salt.salt_client.lookup_jid(jid=jid)
        if ret.status_code == 401:
            raise ValidationError('SaltStack NetAPI Permission required')
        # 返回的内容类似:
        # {u'return': [{u'SERVER6': True}]}
        return ret

    @staticmethod
    def accept_key(minion_id):
        """
        设置master接受minion_id的key
        :return:
        """
        ret = Salt.salt_client.wheel('key.accept', match=minion_id)
        if ret.status_code == 401:
            raise ValidationError('SaltStack NetAPI Permission required')
        return ret

    def add_pillar(self, pillar_dict, **kwargs):
        """
        增加pillar
        :param pillar_dict: 要增加的pillar字典.
        :param kwargs: recursive_update=True, merge_lists=False
        :return:
        """
        if not isinstance(pillar_dict, dict):
            raise ValueError("Dict is required")
        dest_dict = {}
        if self.pillar is not None:
            dest_dict = json.loads(self.pillar)

        self.pillar = json.dumps(dict_merge(deepcopy(dest_dict), pillar_dict, kwargs))
        db.session.add(self)
        db.session.commit()
        return json.dumps(self.pillar or {})

    def get_state(self):
        """
        输出给master_tops的ext_nodes用. yaml格式的输出
        :return:
            classes: [a, b, c.c, d]
        """
        # TODO 确保yaml格式
        return "classes: %s" % self.state

    @staticmethod
    def on_changed_pillar(target, value, oldvalue, initiator):
        current_app.logger.debug(
            "target: %s, old value: %s new value: %s, initiator: %s," % (target, oldvalue, value, initiator))

    @staticmethod
    def on_changed_state(target, value, oldvalue, initiator):
        current_app.logger.debug(
            "target: %s, old value: %s new value: %s, initiator: %s," % (target, oldvalue, value, initiator))

    def __repr__(self):
        return '<Salt %r>' % self.minion_id


db.event.listen(Salt.pillar, 'set', Salt.on_changed_pillar)
db.event.listen(Salt.state, 'set', Salt.on_changed_state)


class DNSRecord(db.Model):
    """
    这里放置部分DNS管理记录, 支持更新到DNSPOD/腾讯云系统. 非全量DNS记录.
    """
    __tablename__ = 'dns_records'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    id = db.Column(db.Integer, primary_key=True)
    sub_domain = db.Column(db.String(64), nullable=False)
    domain = db.Column(db.String(64), default='ops.com')
    value = db.Column(db.String(64), nullable=False)
    record_type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), default='enabled')

    def __repr__(self):
        return '<DNSRecord %r.%r>' % (self.sub_domain, self.domain)
