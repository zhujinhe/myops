# -*- coding: utf8 -*-


import re
import json

from flask import g, current_app, jsonify
from app.exceptions import PermissionError, UnImplemented
from app.auth.views import is_admin

PERMIT = "Permit"
DENY = "Deny"
INDETERMINATE = "Indeterminate"
NOT_APPLICABLE = "NotApplicable"


class ABACBase(object):
    def resource(self):
        """
        子类的实例能够返回该实例的资源标识符和支持的动作标识符.
        以下3个属性以子类中的定义为优先.

        string: __abac_resource_prefix 用来表示资源的前缀
        string: __abac_resource_field_name  代表资源的字段名, 默认为'id'
        list: __abac_action 支持的动作列表.

        :return: (string, list)
        """

        instance_classname = self.__class__.__name__
        resource_type = getattr(self, '_%s__resource_type' % instance_classname, instance_classname.lower())
        resource_field_name = getattr(self, '_%s__resource_field_name' % instance_classname, 'id')
        resource_id = "%s/%s" % (resource_type, getattr(self, '%s' % resource_field_name))
        resource_method_list = getattr(self, '_%s__resource_method_list' % instance_classname,
                                       [func for func in dir(self) if callable(getattr(self, func))
                                        and not func.startswith("_") and not func.startswith("resource")])
        #  "server", "server/1", ["do_action", "do_action2"]
        return resource_type, resource_id, resource_method_list


class StringInArrayComparison(object):
    """
    进行字符串匹配
    """

    def is_in(self, string, target_array):
        """
        严格匹配
        :param string:
        :param target_array:
        :return:
        """
        if isinstance(string, str) and isinstance(target_array, list):
            return string in target_array
        else:
            raise ValueError('wrong type')

    def is_any_regular_match(self, string, pattern_array):
        """
        字符串满足列表中任意一个元素的正则匹配
        :param string: 字符串(不能是正则)
        :param pattern_array: 正则表达式的列表
        :return:
        """
        print('string', string)
        print('pattern_array', pattern_array)

        if isinstance(pattern_array, str):
            pattern_array[0] = pattern_array

        for pattern in pattern_array:
            # TODO 改写为标准的shell类似的匹配.
            rule_match = re.match(pattern.replace("*", ".*"), string, flags=0)
            print("222", rule_match)
            if rule_match:
                print("111", "match success")
                return True
        return False


class ABAC(object):
    """
    Attribute-based access control
    """

    def __init__(self, algorithm='deny_overrides'):
        self.final_decision = DENY
        self.algorithm = algorithm
        self.policy_set = [policy.document for policy in g.current_user.list_all_policies()]

    def evaluate_rule(self, rule, context):
        """
        判断单条rule的鉴定结果.
        :param rule: 单条规则:resource action resource condition
        :param context 上下文
        :return:
        """
        # 获取当前请求的用户, 和策略.
        # 过滤能够应用到当前资源的策略.
        # 判断如果有condiction就判断条件是否满足.
        # 判断是否对动作有权限.
        # 实现拒绝优先策略.

        if getattr(context['resource'], 'resource'):
            resource_type, resource_id, resource_method_list = context['resource'].resource()
        else:
            raise ValueError

        # 判断资源描述符是否匹配规则, 如果不匹配, 则认为本rule不适用.
        resource_comparison = StringInArrayComparison()
        print('00', resource_id, rule['resource'])

        if not resource_comparison.is_any_regular_match(resource_id, rule['resource']):
            return NOT_APPLICABLE

        # TODO 判断condition.

        # 获取资源标识符代表的动作列表, 如果没有符合的动作, 则直接判定为不适用(没有显式允许)
        # "do_action", ["name/server:do_action", "name/server:do_action2"]
        action_string = "name/%s:%s" %(resource_type, context['action'])
        action_comparison = StringInArrayComparison()
        if not action_comparison.is_any_regular_match(action_string, rule["action"]):
            return NOT_APPLICABLE

        # 如果顺利走到最下面, 则认为是允许
        return PERMIT

    def deny_overrides_policy(self, policy, context):
        """
        判断单条策略的判断结果, 任意rule(statement)拒绝则返回拒绝
        :param policy: 单条策略
        :return: 策略结果
        """
        print('policy', policy)

        at_least_one_error = False
        potential_deny = False
        at_least_one_permit = False

        if isinstance(policy, str):
            policy = json.loads(policy)
        if not isinstance(policy, dict):
            raise ValueError('policy error')

        for rule in policy.get('statement', []):
            decision = self.evaluate_rule(rule, context)
            if decision == DENY:
                return DENY
            elif decision == PERMIT:
                at_least_one_permit = True
                continue
            elif decision == NOT_APPLICABLE:
                continue
            elif decision == INDETERMINATE:
                at_least_one_error = True
                if policy['effect'].lower == 'deny':
                    potential_deny = True
                continue

        if potential_deny:
            return INDETERMINATE
        if at_least_one_permit:
            return PERMIT
        if at_least_one_error:
            return INDETERMINATE
        return NOT_APPLICABLE

    def deny_overrides_policy_set(self, policy_set, context):
        """
        策略集合的判断结果, 拒绝优先.
        :param policy_set:
        :param context:
        :return:
        """
        print('policy_set', policy_set)

        at_least_one_permit = False
        for policy in policy_set:
            if isinstance(policy, str):
                policy = json.loads(policy)
            decision = self.deny_overrides_policy(policy, context)
            if decision == DENY:
                return DENY
            elif decision == PERMIT:
                at_least_one_permit = True
            elif decision == NOT_APPLICABLE:
                continue
            elif decision == INDETERMINATE:
                return DENY
        if at_least_one_permit:
            return PERMIT
        return NOT_APPLICABLE

    def evaluate(self, context):
        """
        获取最终的执行结果.
        :param context context是请求内容, 最终会传给evaluate_rule.
        示例
        context = {"subject": g.current_user,
               "resource": server,
               "action": "do_action",
               "environment": request
               }
        :return: boolean
        """
        # if is_admin():
        #     return True

        if self.algorithm == 'deny_overrides':
            self.final_decision = self.deny_overrides_policy_set(self.policy_set, context)
        else:
            raise UnImplemented('Unimplemented Overrides Policy Combining Algorithm')
        return self.final_decision == PERMIT
        # return True

    def permit_or_raise(self, context):
        if self.evaluate(context):
            return True
        else:
            raise PermissionError('Permission denied')
