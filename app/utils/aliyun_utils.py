# -*- coding: utf8 -*-
from config import Config
from aliyunsdkcore import client
from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest, DescribeInstanceAttributeRequest
from aliyunsdkslb.request.v20140515 import DescribeLoadBalancersRequest, DescribeLoadBalancerAttributeRequest, \
    DescribeLoadBalancerTCPListenerAttributeRequest, DescribeLoadBalancerUDPListenerAttributeRequest, \
    DescribeLoadBalancerHTTPListenerAttributeRequest, DescribeLoadBalancerHTTPSListenerAttributeRequest
import json


# TODO: 后续改成根据一个字典配置,动态生成的.

def get_aliyun_client(region_id=Config.aliyun_region[0], readonly=True):
    """
    阿里云SDK client, 可区分是否用只读账号
    :param region_id: 默认使用'cn-hangzhou'
    :param readonly: 是否使用只读账号
    :return:
    """

    if readonly:
        ak = Config.aliyun_readonly_access_key
        secret = Config.aliyun_readonly_secret
    else:
        ak = Config.aliyun_full_access_key
        secret = Config.aliyun_full_secret
    return client.AcsClient(ak=ak, secret=secret, region_id=region_id)


def get_aliyun_ecs(region_id):
    """
    获取某个可用区的完整服务器信息列表
    :param region_id:
    :return:
    """
    ecs_instances = []
    page_number = 1
    page_size = 10

    aliyun_client = get_aliyun_client(region_id=region_id)
    # 获取完整的Instances列表
    while True:
        aliyun_request = DescribeInstancesRequest.DescribeInstancesRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_PageSize(page_size)
        aliyun_request.add_query_param('PageNumber', page_number)
        aliyun_request.add_query_param('RegionId', region_id)
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        response_data = json.loads(aliyun_response)

        ecs_instances.extend(response_data['Instances']['Instance'])

        total_count = response_data['TotalCount']
        page_size = response_data['PageSize']

        if total_count < page_number * page_size:
            break

        page_number += 1

    return ecs_instances


def get_aliyun_ecs_by_instance_id(instance_id):
    """
    根据可用区ID和实例ID查询实例属性
    :param instance_id:
    :return:
    """
    aliyun_client = get_aliyun_client()
    # 获取实例属性.
    aliyun_request = DescribeInstanceAttributeRequest.DescribeInstanceAttributeRequest()
    aliyun_request.set_accept_format('json')
    aliyun_request.set_InstanceId(instance_id)

    aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
    return json.loads(aliyun_response)


def get_aliyun_slb_by_loadbalancer_id(loadbalancer_id):
    """
    获取slb的实例属性
    :param loadbalancer_id:
    :return:
    """
    aliyun_client = get_aliyun_client()
    # 获取实例属性.
    aliyun_request = DescribeLoadBalancerAttributeRequest.DescribeLoadBalancerAttributeRequest()
    aliyun_request.set_accept_format('json')
    aliyun_request.set_LoadBalancerId(loadbalancer_id)

    aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
    return json.loads(aliyun_response)


def get_aliyun_slb(region_id):
    """
    获取某个区域的负载均衡信息列表
    :param region_id:
    :return:
    """
    loadbalancers = []
    page_number = 1
    page_size = 10

    aliyun_client = get_aliyun_client(region_id=region_id)

    # 获取完整的LoadBalancer列表
    while True:
        aliyun_request = DescribeLoadBalancersRequest.DescribeLoadBalancersRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.add_query_param('PageSize', page_size)
        aliyun_request.add_query_param('PageNumber', page_number)
        aliyun_request.add_query_param('RegionId', region_id)
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        response_data = json.loads(aliyun_response)

        loadbalancers.extend(response_data['LoadBalancers']['LoadBalancer'])

        total_count = response_data['TotalCount']
        page_size = response_data['PageSize']

        if total_count < page_number * page_size:
            break

        page_number += 1

    return loadbalancers


def get_aliyun_slb_listeners_by_loadbalancer_id(loadbalancer_id):
    """
    获取某个slb下面的listeners的属性.
    :param loadbalancer_id:
    :return: protocol, port, attribute
    """
    loadbalancer = get_aliyun_slb_by_loadbalancer_id(loadbalancer_id)
    listeners = loadbalancer['ListenerPortsAndProtocol']['ListenerPortAndProtocol'] or []
    ret = []

    for listener in listeners:
        aliyun_client = get_aliyun_client()
        if listener['ListenerProtocol'] == 'tcp':
            aliyun_request = DescribeLoadBalancerTCPListenerAttributeRequest.DescribeLoadBalancerTCPListenerAttributeRequest()
        elif listener['ListenerProtocol'] == 'udp':
            aliyun_request = DescribeLoadBalancerUDPListenerAttributeRequest.DescribeLoadBalancerUDPListenerAttributeRequest()
        elif listener['ListenerProtocol'] == 'http':
            aliyun_request = DescribeLoadBalancerHTTPListenerAttributeRequest.DescribeLoadBalancerHTTPListenerAttributeRequest()
        elif listener['ListenerProtocol'] == 'https':
            aliyun_request = DescribeLoadBalancerHTTPSListenerAttributeRequest.DescribeLoadBalancerHTTPSListenerAttributeRequest()
        aliyun_request.set_accept_format('json')
        aliyun_request.set_LoadBalancerId(loadbalancer_id)
        aliyun_request.set_ListenerPort(listener['ListenerPort'])
        aliyun_response = aliyun_client.do_action_with_exception(aliyun_request)
        listener_attribute = json.loads(aliyun_response)

        ret.append((listener['ListenerProtocol'], listener['ListenerPort'], listener_attribute))
    return ret
