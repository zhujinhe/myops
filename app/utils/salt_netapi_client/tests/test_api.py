# -*- coding: utf8 -*-

from app.utils.salt_netapi_client import SaltNetAPIClient
from config import Config

salt_instance = SaltNetAPIClient(Config.salt_url, username=Config.salt_pam_username, password=Config.salt_pam_password,
                                 eauth='pam')

print salt_instance.local('SERVER6', 'test.ping').text
