# -*- coding: utf8 -*-
import taskflow.engines
import taskflow.retry

from taskflow.patterns import linear_flow, unordered_flow, graph_flow
from .tasks import *


def flow_init_server_ops_api():
    flow = linear_flow.Flow('init_server_ops_api').add(
        unordered_flow.Flow('init').add(
            ServerInfoUpdate('server_update'),
            SLBInfoUpdate('slb_b_update', rebind=dict(loadbalancer_id='b_loadbalancer_id')),
            SLBInfoUpdate('slb_a_update', rebind=dict(loadbalancer_id='a_loadbalancer_id')),
        ),
        SaltStateApply('salt_state_apply', requires=['instance_id', 'state_lists']),
        GitlabTriggerBuild('gitlab_build', requires=['gitlab_project_id', 'gitlab_token', 'gitlab_ref', 'CUSTOM_SSH_HOST'],
                           rebind=dict(CUSTOM_SSH_HOST='server_public_ip')),
        InstanceAddToCMSWhiteList('cms_add_ips', requires=['instance_id']),
        InstanceAddToSLBWhiteList('slb_add_ips', rebind=dict(loadbalancer_id='b_loadbalancer_id',
                                                             loadbalancer_port='b_loadbalancer_port',
                                                             instance_ips='server_inner_ip')),
        InstanceAddToSLB('slb_add_instance', rebind=dict(loadbalancer_id='a_loadbalancer_id'))
    )
    return flow
