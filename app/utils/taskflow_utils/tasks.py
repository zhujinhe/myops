# -*- coding: utf8 -*-

# taskflow
from taskflow import task

# ops
from app.assets.models import Server, LoadBalancer, LoadBalancerListener
from app.utils.gitlab_utils import trigger_build


class ServerInfoUpdate(task.Task):
    default_provides = 'server_public_ip', 'server_inner_ip'

    def execute(self, instance_id):
        """
        初始化单个服务器信息
        """
        Server.update_by_id(instance_id)
        instance = Server.query.filter_by(instance_id=instance_id).first()
        if instance is not None:
            return instance.public_ip_address, instance.inner_ip_address
        return False


class SLBInfoUpdate(task.Task):
    def execute(self, loadbalancer_id):
        """
        初始化slb和listener信息.
        :return:
        """
        LoadBalancer.update_by_id(loadbalancer_id, update_listener=True)
        return True


class InstanceAddPillar(task.Task):
    default_provides = 'instance_pillar'

    def execute(self, instance_id, pillar_dict, **kwargs):
        """
        给某个服务器增加pillar.
        :param instance_id:
        :param pillar:
        :return:
        """
        instance = Server.query.filter_by(instance_id=instance_id).first()
        if instance is not None:
            instance.salt_key_accept()
            instance.add_pillar(pillar_dict=pillar_dict)
            return True
        return False


class SaltStateApply(task.Task):
    default_provides = 'instance_state_apply'

    def execute(self, instance_id, state_lists):
        """
        应用state列表中的state
        :param instance_id:
        :param state_lists:
        :return:
        """
        server = Server.query.filter_by(instance_id=instance_id).first()
        if server is not None:
            # 初始化服务器,并启动服务（nginx, php-fpm)
            ret = []
            server.salt_key_accept()
            for state in state_lists:
                ret.append(server.local('state.sls', state).text)
            return ret
        return False


class GitlabTriggerBuild(task.Task):
    default_provides = 'gitlab_trigger_build'

    def execute(self, gitlab_project_id, gitlab_token, gitlab_ref, **variables):
        """
        gitlab触发一次发布
        :return:
        """
        print "GitlabTriggerBuild variables", variables
        return trigger_build(gitlab_project_id, gitlab_token, gitlab_ref, **variables)


class InstanceAddToSLBWhiteList(task.Task):
    def execute(self, loadbalancer_id, loadbalancer_port, instance_ips):
        """
        增加SLB白名单授权IP。（阿里云负载均衡里面添加API内网IP地址）
        :param loadbalancer_id:
        :param loadbalancer_port:
        :param instance_ips:
        :return:
        """
        loadbalancer_listener = LoadBalancerListener.query.filter(
            LoadBalancerListener.loadbalancer_id == loadbalancer_id,
            LoadBalancerListener.listener_port == loadbalancer_port).first()
        if loadbalancer_listener is not None:
            loadbalancer_listener.set_listener_access_control_status(status='open_white_list')
            loadbalancer_listener.add_white_list_items(instance_ips)
            return True
        return False


class InstanceAddToCMSWhiteList(task.Task):
    def execute(self, instance_id):
        # # 添加短信通道白名单
        server = Server.query.filter_by(instance_id=instance_id).first()
        if server is not None:
            server.add_yuntongxun_white_list()
            return True
        return False


class InstanceAddToSLB(task.Task):
    def execute(self, instance_id, loadbalancer_id):
        # 增加到阿里云负载均衡。
        loadbalancer = LoadBalancer.query.filter_by(loadbalancer_id=loadbalancer_id).first()
        if loadbalancer is not None:
            loadbalancer.add_backend_servers([instance_id])
            return True
        return False
