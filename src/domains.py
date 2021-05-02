"""
Author: Enigma Zhang

Description:
    This module validates models in database of this app.
"""

from cerberus import Validator

v = Validator(require_all=True)


def user_validation(document):
    schema = {
        "name":
            {"type": "string", "regex": "[\u00ff-\uffff0-9a-zA-z]+", "min": 1, "max": 32},
        "phoneNumber":
            {"type": "string", "regex": "[0-9]+", "min": 1, "max": 20},
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
            {"type": "string", "regex": "[\u00ff-\uffff0-9a-zA-z]+", "min": 1, "max": 32},
        "members":
            {"type": "list"},
        "message_num":
            {"type": "integer"},
        "room_message_id":
            {"type": "list"}
    }
    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!\n" + str(document))


def message_validation(document):
    schema = {
        "userId":
            {"type": "string", "regex": "^[0-9a-fA-F]{24}$"},
        "roomId":
            {"type": "string", "regex": "^[0-9a-fA-F]{24}$"},
        "message_type":
            {"type": "string", "allowed": ["text", "image", "file"]},
        "content":
            {}
    }

    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!\n" + str(document))


def login_validation(document):
    schema = {
        "phoneNumber":
            {"type": "string", "regex": "[0-9]+", "min": 1, "max": 20},
        "password":
            {"type": "string", "regex": "[0-9a-zA-z]+", "min": 1, "max": 32}
    }

    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!\n" + str(document))
