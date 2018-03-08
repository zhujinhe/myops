# -*- coding: utf8 -*-
import requests
import json
from .exceptions import SaltNetAPIConnectionError, SaltNetAPIAuthenticationError


class SaltNetAPIClient(object):
    """
    Represents a SaltStack NetAPI connection. inspect by pepper
    A thin wrapper for making HTTP calls to the salt-api REST_CHERRYPY REST interface
    # 权限设置在/etc/salt/master.d/eauth.conf
    # server端设置/etc/salt/master.d/rest_cherrypy.conf
    """

    def __init__(self, url, private_token=None, username=None, password=None,
                 eauth=None, ssl_verify=True, timeout=None):
        # The token may be sent in one of two ways: as a custom header or as a session
        # cookie. The latter is far more convenient for clients that support cookies.

        # url of salt netapi
        self._url = url.rstrip('/')
        # use private_token as primary
        self.private_token = private_token
        #: timeout to use for requests to salt netapi
        self.timeout = timeout
        #: Headers that will be used in request to salt netapi
        self.headers = {}
        #: The user username, password, eauth pairs
        self.username = username
        self.password = password
        self.eauth = eauth
        #: Whether SSL certificates should be validated
        self.ssl_verify = ssl_verify
        # generate token
        self.set_token(private_token)
        #: Create a session object for requests
        self.session = requests.Session()

    def auth(self):
        """Performs an authentication.
        Uses either the private token, or the username/password pair.
        """
        if self.private_token and (self._raw_get('/stats').status_code == '200'):
            self.token_auth()
        else:
            self.credentials_auth()

    def logout(self):
        self._raw_post('/logout')

    def set_token(self, token):
        """Sets the private token for authentication.
        Args:
            token (str): The private token.
        """
        self.private_token = token if token else None

        if token:
            self.headers["X-Auth-Token"] = token
        elif "X-Auth-Token" in self.headers:
            del self.headers["X-Auth-Token"]

    def token_auth(self):
        self.set_token(self.private_token)

    def credentials_auth(self):
        """Performs an authentication using username/password."""
        if not self.username or not self.password:
            raise SaltNetAPIAuthenticationError("Missing username/password")
        data = json.dumps({'username': self.username, 'password': self.password, 'eauth': self.eauth})
        r = self._raw_post('/login', data, content_type='application/json')
        self.set_token(r.json().get('return', [{}])[0]['token'])

    def _create_headers(self, content_type=None):
        request_headers = self.headers.copy()
        if content_type is not None:
            request_headers['Content-type'] = content_type
        return request_headers

    def _get_session_opts(self, content_type):
        return {
            'headers': self._create_headers(content_type),
            'timeout': self.timeout,
            'verify': self.ssl_verify
        }

    def _raw_get(self, path_, content_type=None, streamed=False, **kwargs):
        if path_.startswith('http://') or path_.startswith('https://'):
            url = path_
        else:
            url = '%s%s' % (self._url, path_)

        opts = self._get_session_opts(content_type)
        try:
            return self.session.get(url, params=kwargs, stream=streamed,
                                    **opts)
        except Exception as e:
            raise SaltNetAPIConnectionError(
                "Can't connect to SaltNetApi server (%s)" % e)

    def _raw_post(self, path_, data=None, content_type=None, **kwargs):
        url = '%s%s' % (self._url, path_)
        opts = self._get_session_opts(content_type)
        try:
            return self.session.post(url, params=kwargs, data=data, **opts)
        except Exception as e:
            raise SaltNetAPIConnectionError(
                "Can't connect to SaltNetApi server (%s)" % e)

    # functions of salt netapi.
    def low(self, lowstate, path='/'):
        """
        Execute a command through salt-api and return the response
        :param string path: URL path to be joined with the API hostname
        :param list lowstate: a list of lowstate dictionaries
        """
        return self._raw_post(path, data=json.dumps(lowstate), content_type='application/json')

    def local(self, tgt, fun, arg=None, kwarg=None, expr_form='glob',
              timeout=None, ret=None):
        """
        Run a single command using the ``local`` client
        Wraps :method:`low`.
        expr_form:
            - glob
            - pcre
            - grain
            - grain_pcre
            - compound
            - pillar
            - pillar_pcre
        """
        low = {
            'client': 'local',
            'tgt': tgt,
            'fun': fun,
        }

        if arg:
            low['arg'] = arg

        if kwarg:
            low['kwarg'] = kwarg

        if expr_form:
            low['expr_form'] = expr_form

        if timeout:
            low['timeout'] = timeout

        if ret:
            low['ret'] = ret

        return self.low([low], path='/')

    def local_async(self, tgt, fun, arg=None, kwarg=None, expr_form='glob',
                    timeout=None, ret=None):
        """
        Run a single command using the ``local_async`` client
        Wraps :method:`low`.
        """
        low = {
            'client': 'local_async',
            'tgt': tgt,
            'fun': fun,
        }

        if arg:
            low['arg'] = arg

        if kwarg:
            low['kwarg'] = kwarg

        if expr_form:
            low['expr_form'] = expr_form

        if timeout:
            low['timeout'] = timeout

        if ret:
            low['ret'] = ret

        return self.low([low], path='/')

    def local_batch(self, tgt, fun, arg=None, kwarg=None, expr_form='glob',
                    batch='50%', ret=None):
        """
        Run a single command using the ``local_batch`` client

        Wraps :method:`low`.
        """
        low = {
            'client': 'local_batch',
            'tgt': tgt,
            'fun': fun,
        }

        if arg:
            low['arg'] = arg

        if kwarg:
            low['kwarg'] = kwarg

        if expr_form:
            low['expr_form'] = expr_form

        if batch:
            low['batch'] = batch

        if ret:
            low['ret'] = ret

        return self.low([low], path='/')

    def lookup_jid(self, jid):
        """
        Get job results
        Wraps :method:`runner`.
        """

        return self.runner('jobs.lookup_jid', jid='{0}'.format(jid))

    def runner(self, fun, **kwargs):
        """
        Run a single command using the ``runner`` client
        Usage::
          runner('jobs.lookup_jid', jid=20170103180845963699)
        """
        low = {
            'client': 'runner',
            'fun': fun,
        }

        low.update(kwargs)

        return self.low([low], path='/')

    def wheel(self, fun, arg=None, kwarg=None, **kwargs):
        """
        Run a single command using the ``wheel`` client
        Usage::
          wheel('key.accept', match='minion_id')
        """
        low = {
            'client': 'wheel',
            'fun': fun,
        }
        if arg:
            low['arg'] = arg
        if kwarg:
            low['kwarg'] = kwarg
        low.update(kwargs)
        return self.low([low], path='/')
