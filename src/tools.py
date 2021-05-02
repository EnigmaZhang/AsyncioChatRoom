import bcrypt
import jwt.api_jwt
import datetime
import tornado.log

"""
Author: Enigma Zhang

Description:
    This module is various tools of app.
"""


def objectIdToStr(d):
    """
        Convert ObjectId in the dict to string type to dumped by json.
    """
    d["_id"] = str(d["_id"])


class Encryption:
    """
        Encryption password and validates password.
    """

    @staticmethod
    def encryption(password):
        password = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hash_result = bcrypt.hashpw(password, salt)
        return hash_result

    @staticmethod
    def validation(plain, password):
        plain = plain.encode("utf-8")
        return bcrypt.checkpw(plain, password)


def token_generate(uid, expired_time=86400):
    key = "secret"
    timestamp = int(datetime.datetime.utcnow().timestamp())
    payload = {
        "uid": uid,
        "iss": "ENIGMA",
        "aud": "ENIGMA",
        "iat": int(timestamp),
        "exp": int(timestamp + expired_time)
    }
    encoded = jwt.api_jwt.encode(payload=payload, key=key, algorithm="HS256")
    return encoded


def token_validation(encoded):
    try:
        payload = jwt.api_jwt.decode(encoded, key="secret",
                                     algorithms="HS256",
                                     audience="ENIGMA",
                                     iss="ENIGMA")
    except jwt.InvalidTokenError:
        return None
    return payload["uid"]


async def auth_with_token(my_redis, authorization):
    uid = token_validation(authorization)
    if uid:
        if await my_redis.exists(uid) is True:
            return (await my_redis.get(uid)).decode() == authorization
    return False
