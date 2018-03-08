#!/bin/env python
# -*- coding: utf8 -*-

import requests
import re
import urllib


def generate_md5(plaintext):
    import hashlib
    m = hashlib.md5()
    m.update(plaintext)
    return m.hexdigest()


class YunTongXunClient(object):
    """
    编辑云通讯白名单
    """
    login_header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'http://www.yuntongxun.com/user/login',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6'
    }

    ip_auth_header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Accept': 'text/html, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
        'Referer': 'http://www.yuntongxun.com/member/main',
        'X-Requested-With': 'XMLHttpRequest'
    }

    edit_ips_header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'http://www.yuntongxun.com/member/main',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6'
    }

    def __init__(self, username, password):
        self.login_url = 'http://www.yuntongxun.com/user/login'
        self.do_login_url = 'http://www.yuntongxun.com/user/doLogin'
        self.get_ip_url = 'http://www.yuntongxun.com/member/toIpAuthDispose'
        self.do_edit_url = 'http://www.yuntongxun.com/member/ipAuthDispose'
        self.username = username
        self.password = password
        self.session = requests.Session()

        # 初始化请求, 并获取账号和加密之后的密码
        resp_int = self.session.get(url=self.login_url)
        self.get_password(self.re_get_captcha(resp_int.text))
        login_data = {
            "loginName": self.username,
            "loginPwd": self.get_password(self.re_get_captcha(resp_int.text)),
            "remeberMe": 'on',
            "preUrl": 'toMain'
        }
        # 登录, 并获取验证码(修改cookies等)
        self.session.post(url=self.do_login_url, data=urllib.urlencode(login_data), headers=self.login_header,
                          verify=False)

    def get_password(self, captcha):
        return generate_md5(generate_md5(generate_md5(self.password) + self.username) + captcha)

    def re_get_captcha(self, text):
        pattern = re.compile(r'var j_captcha= "(?P<captcha>\w{4})";')
        match = pattern.search(text)
        if match:
            return match.group('captcha')

    def re_get_token(self, text):
        pattern = re.compile(r'<input type="hidden" name="token" value="(?P<token>\w{32})"/>')
        match = pattern.search(text)
        if match:
            return match.group('token')

    def re_get_ips(self, text):
        pattern = re.compile(r'<textarea  class="adr_text" name="ips" id="ips">(?P<ips>[0-9,.]+)</textarea>')
        match = pattern.search(text)
        if match:
            return match.group('ips')

    def get_ips_and_token(self):
        # 获取现有IP列表和隐藏的token
        resp_ip_auth = self.session.get(url=self.get_ip_url, headers=self.ip_auth_header, verify=False)
        ips = self.re_get_ips(resp_ip_auth.text)
        ip_auth_token = self.re_get_token(resp_ip_auth.text)
        if ip_auth_token is None:
            raise ValueError
        return ips, ip_auth_token

    def add_ips(self, ips):
        """
        增加IP白名单
        :param ips:以逗号分隔的IP列表.或者ip的list.
        :return:
        """
        ips_current, ip_auth_token = self.get_ips_and_token()
        # 去空格, 重新拼装.
        new_ips = []
        for ip in ips_current.split(','):
            new_ips.append(ip.strip())
        if isinstance(ips, str):
            for ip in ips.split(','):
                new_ips.append(ip.strip())
        elif isinstance(ips, list):
            new_ips.extend(ips)
        if len(list(set(new_ips))) > 50:
            raise ValueError
        new_ips = ','.join(list(set(new_ips)))

        # 发起修改的请求
        ip_auth_data = {
            "isIpAuth": 1,
            "token": ip_auth_token,
            "ips": new_ips
        }
        # print ip_auth_token, new_ips
        edit_ips = self.session.post(url=self.do_edit_url, data=urllib.urlencode(ip_auth_data),
                                     headers=self.edit_ips_header,
                                     verify=False)
        # 重新获取IP的列表返回
        return self.get_ips_and_token()[0]

# ytx = YunTongXunClient(yuntongxun_username, yuntongxun_password)
# print ytx.add_ips('4.3.2.1')
