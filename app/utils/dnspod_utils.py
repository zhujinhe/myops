# -*- coding: utf8 -*-
from config import Config
import requests
from app.exceptions import DNSPodError


# dnspod api wrapper
def _dnspod_post_api(uri, **kwargs):
    default_payloads = {"login_token": Config.dnspod_token,
                        "format": "json",
                        "lang": "en",
                        "error_on_empty": "no",
                        }
    payloads = dict(default_payloads.items() + kwargs.items())

    r = requests.post(url=Config.dnspod_domain + uri, data=payloads)
    try:
        # 确保返回的值格式正确
        if r.status_code != 200:
            raise DNSPodError
        if r.json()['status']['code'] != '1':
            raise DNSPodError
        return r.json()
    except:
        raise DNSPodError


def get_dnspod_record(domain=Config.ops_domain, sub_domain=None):
    """
    查询当前的dns设置
    """
    record_list = _dnspod_post_api(uri='Record.List', domain=domain, sub_domain=sub_domain)
    if len(record_list['records']) < 1:
        return None
    return record_list['records'][0]


def set_dnspod_record(domain=Config.ops_domain, sub_domain=None, value=None, record_type='A', record_line='默认'):
    """
    DNSPod的接口有频次限制,需要先获取到值,对比做响应动作.
    :return:
    """
    record = get_dnspod_record(domain=domain, sub_domain=sub_domain)

    if record is None:
        return _dnspod_post_api(uri='Record.Create', domain=domain, sub_domain=sub_domain,
                                record_type=record_type, record_line=record_line, value=value
                                )
    if record['value'] == value:
        if record['enabled'] == '1':
            return record
    else:
        return _dnspod_post_api(uri='Record.Modify', domain=domain,
                                sub_domain=sub_domain, record_id=record['id'],
                                record_type=record_type, record_line=record_line, value=value)


def disable_dnspod_record(domain=Config.ops_domain, sub_domain=None):
    """
    设置为禁用状态, 暂时不写删除操作
    """
    record = get_dnspod_record(domain=domain, sub_domain=sub_domain)
    if record is not None:
        return _dnspod_post_api(uri='Record.Modify', domain=domain,
                                sub_domain=sub_domain, record_id=record['id'],
                                record_type=record['type'], record_line=record['line_id'],
                                value=record['value'], status='disable')
