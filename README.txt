运维系统的半成品demo

可以作为一个统一的操作中心, 打通各个孤立的运维组件, 在保证权限控制的前提下提高运维的效率, 沉淀流程制度.
可以很方便的增加组件.

功能:
基于属性的访问控制(关键部分还未完成).
基础的配置管理,可以调用公有云接口动态更新.
通过阿里云的sdk支持云资源的常规操作,如操作服务器,负载均衡,网络安全组.
打通saltstack, 可以在运维中心匹配pillar, 下发状态和执行操作, 达到服务器级别的控制.
支持dnspod的解析记录的管理.
支持某短信厂商修改白名单.
支持触发gitlab中的集成.
支持自定义的任务流执行和失败回滚.
支持传入json数据的schema预定义检查.

用到的主要组件:
taskflow, 用来自定义任务流的执行和失败回滚.(刚开始用的celery,后改用的taskflow)
flask/sqlalchemy/mysql/redis. web使用python的一个开源框架.
saltstack netapi. 通过自定义的salt module和netapi双向打通. salt formular仍然用salt管理,这里做pillar和命令下发.
aliyun sdk. 管理阿里云的服务器.
jsonschema. 保证输入格式的正确, 也能根据格式反向生成需要的schema.

后续计划:
现有的权限认证没写, 计划改为类似ABAC认证方式.
只有后端, 前端考察了一下react,看上去比较适合, 后续增加.
可能会把资产管理与其他附件关联解耦开.
支持更多的组件,比如zabbix, elk.
