# -*- coding: utf8 -*-
from flask import jsonify
from app.exceptions import ValidationError, PermissionError
from .views import auth


def bad_request(message):
    response = jsonify({'error': 'bad request', 'message': message})
    response.status_code = 400
    return response


def unauthorized(message='please authenticate'):
    response = jsonify({'status': 401, 'error': 'unauthorized',
                        'message': message})
    response.status_code = 401
    return response


@auth.app_errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])


@auth.app_errorhandler(404)  # this has to be an app-wide handler
def not_found(e):
    response = jsonify({'status': 404, 'error': 'not found',
                        'message': 'invalid resource URI'})
    response.status_code = 404
    return response


@auth.errorhandler(405)
def method_not_supported(e):
    response = jsonify({'status': 405, 'error': 'method not supported',
                        'message': 'the method is not supported'})
    response.status_code = 405
    return response


@auth.app_errorhandler(500)  # this has to be an app-wide handler
def internal_server_error(e):
    response = jsonify({'status': 500, 'error': 'internal server error',
                        'message': e.args[0]})
    response.status_code = 500
    return response
