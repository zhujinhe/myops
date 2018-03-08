# -*- coding: utf8 -*-
"""
暂时先用requests模拟,后续如果需要的接口比较多,就用python-gitlab
"""
import requests


def trigger_build(project_id, gitlab_token, gitlab_ref, gitlab_host='https://gitlab.ops.com', **variables):
    gitlab_url = '%s/api/v3/projects/%s/trigger/builds' % (gitlab_host, project_id)
    payloads = {'token': gitlab_token,
                'ref': gitlab_ref}
    for k, v in variables.items():
        payloads[str('variables[' + k + ']')] = v

    print "payloads, url", payloads, gitlab_url

    gitlab_request = requests.post(url=gitlab_url,
                                   data=payloads)
    ret = gitlab_request.json()
    return ret
