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
            {"type": "string", "regex": "[^\x00-\xff0-9a-zA-z]+", "min": 1, "max": 32},
        "phoneNumber":
            {"regex": "[0-9]+", "min": 1, "max": 20},
        "password":
            {"type": "string", "regex": "[0-9a-zA-z]+", "min": 1, "max": 32},
        "rooms":
            {"type": "dict"}
    }
    if not v.validate(document, schema):
        raise ValueError("User argument validation failed!" + str(document))


class MessageValidator:
    pass
