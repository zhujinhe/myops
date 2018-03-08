# -*- coding: utf-8 -*-
'''
A module that adds data to the Pillar structure retrieved by an http request


Configuring the HTTP_JSON ext_pillar
====================================

Set the following Salt config to setup http json result as external pillar source:

.. code-block:: yaml
  ext_pillar:
    - http_json:
        url: http://example.com/api/%s
        username: basic username
        password: basic password

Module Documentation
====================
'''

# Import python libs
from __future__ import absolute_import
import logging
import re

# Import Salt libs
try:
    from salt.ext.six.moves.urllib.parse import quote as _quote

    _HAS_DEPENDENCIES = True
except ImportError:
    _HAS_DEPENDENCIES = False

# Set up logging
_LOG = logging.getLogger(__name__)


def __virtual__():
    return _HAS_DEPENDENCIES


def ext_pillar(minion_id,
               pillar,  # pylint: disable=W0613
               url,
               username=None,
               password=None):
    '''
    Read pillar data from HTTP response.

    :param str url: Url to request.
    :param str username: username for basic auth
    :param str password: password for basic auth
    :return: A dictionary of the pillar data to add.
    :rtype: dict
    '''

    url = url.replace('%s', _quote(minion_id))

    _LOG.debug('Getting url: %s', url)

    if username and password:
        data = __salt__['http.query'](url=url, username=username, password=password, decode=True, decode_type='json')
    else:
        data = __salt__['http.query'](url=url, decode=True, decode_type='json')

    if 'dict' in data:
        return data['dict']

    _LOG.error("Error on minion '%s' http query: %s\nMore Info:\n", minion_id, url)

    for key in data:
        _LOG.error('%s: %s', key, data[key])

    return {}
