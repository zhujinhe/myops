# -*- coding: utf8 -*-
import jsonschema
import json
from app.exceptions import ValidationError
from app.utils.helpers import get_full_path


def json_schema_validator(json_data, json_schema):
    if isinstance(json_data, dict):
        json_data = json.dumps(json_data)

    if not json_data or not json_schema:
        raise ValidationError("Missing json_data or json_schema")

    try:
        jsonschema.validate(json.loads(json_data), json.loads(json_schema))
    except jsonschema.SchemaError as e:
        raise ValidationError("SchemaError: %s" % e.message)
    except jsonschema.ValidationError as e:
        raise ValidationError("JSON ValidationError: %s" % e.message)
    else:
        return True


def json_schema_validator_by_filename(json_data, json_schema_filename, json_schema_file_path='app/utils/json_schema'):
    """
    默认从'app/utils/json_schema'目录里读取文件内容做验证.
    """
    try:
        json_schema_file_full_path = get_full_path(json_schema_file_path, json_schema_filename)
        with open(json_schema_file_full_path) as f:
            json_schema = f.read()
    except IOError, e:
        raise ValidationError('Invalid json schema file path', e)
    return json_schema_validator(json_data, json_schema)


def generate_json_schema(json_data, **kwargs):
    if isinstance(json_data, dict):
        json_data = json.dumps(json_data)
    if isinstance(json_data, str):
        try:
            from json_schema_generator import SchemaGenerator
            json.dumps(json_data)
        except:
            raise ValueError
        json_schema = SchemaGenerator.from_json(json_data)
        return json_schema.to_json(**kwargs)
