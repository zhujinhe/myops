from base64 import b64encode
import json
from urlparse import urlsplit, urlunsplit

class TestClient():
    def __init__(self, app, username, password):
        self.app = app
        self.auth = 'Basic ' + b64encode((username + ':' + password)
                                         .encode('utf-8')).decode('utf-8')

    def send(self, url, method='GET', data=None, headers=None):
        # for testing, URLs just need to have the path and query string
        url_parsed = urlsplit(url)
        url = urlunsplit(('', '', url_parsed.path, url_parsed.query,
                          url_parsed.fragment))

        # append the headers to all requests
        if headers is not None:
            headers = headers.copy()
        else:
            headers = {}
        headers['Authorization'] = self.auth
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'

        # convert JSON data to a string
        if data:
            data = json.dumps(data)

        # send request to the test client and return the response
        with self.app.test_request_context(url, method=method, data=data,
                                           headers=headers):
            rv = self.app.preprocess_request()
            if rv is None:
                rv = self.app.dispatch_request()
            rv = self.app.make_response(rv)
            rv = self.app.process_response(rv)
            return rv, json.loads(rv.data.decode('utf-8'))

    def get(self, url, headers=None):
        return self.send(url, 'GET', headers=headers or {})

    def post(self, url, data, headers=None):
        return self.send(url, 'POST', data, headers=headers or {})

    def put(self, url, data, headers=None):
        return self.send(url, 'PUT', data, headers=headers or {})

    def delete(self, url, headers=None):
        return self.send(url, 'DELETE', headers=headers or {})
