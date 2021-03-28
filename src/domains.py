"""
Author: Enigma Zhang

Description:
    This module validates models in database of this app.
"""

from cerberus import Validator

v = Validator()


def user_validation(document):
    schema = {
        "name":
            {"type": "string", "regex": "[\x00-\xff0-9a-zA-z]+", "min": 1, "max": 32},
        "phoneNumber":
            {"regex": "[0-9]+", "min": 1, "max": 20},
        "password":
            {"type": "string", "regex": "[0-9a-zA-z]+", "min": 1, "max": 32},
        "rooms":
            {"type": "list"}
    }
    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!\n" + str(document))


def room_validation(document):
    schema = {
        "name":
            {"type": "string", "regex": "[\x00-\xff0-9a-zA-z]+", "min": 1, "max": 32},
        "members":
            {"type": "list"},
        "message_num":
            {"type": "integer"}
    }
    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!\n" + str(document))

