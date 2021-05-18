import asyncio
import datetime
import json
import math
from abc import ABC
from typing import Optional, Awaitable, Any
import os

import aredis
import bson
import jwt
import motor
import pymongo
import tornado.ioloop
import tornado.log
import tornado.web
import tornado.autoreload
from bson.objectid import ObjectId
from tornado import httputil
from tornado.web import Application

import domains
from tools import objectIdToStr, Encryption, token_generate, auth_with_token

"""
Author: Enigma Zhang

Description:
    This module is the main file of app which defines settings, routers and API handlers.
"""


class BaseHandler(tornado.web.RequestHandler, ABC):

    def prepare(self) -> Optional[Awaitable[None]]:
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if "Authorization" in self.request.headers.keys() and self.request.headers["Authorization"]:
            if self.request.headers["Authorization"].startswith("Bearer"):
                self.request.headers["Authorization"] = self.request.headers["Authorization"].split()[1].strip()
        return super().prepare()

    async def get(self, *args, **kwargs):
        try:
            self.write("""
            <html>
            <head>
            <meta charset="utf-8">
            <title>AsyncioChatroom</title>
            </head>
            <body>
                Hello World! Welcome to the chatroom! The frontend is at port 9200.
            </body>
            </html>
                            """)
        except asyncio.CancelledError:
            self.set_status(404)
            return
        self.set_status(403)
        return


class UserHandler(BaseHandler, ABC):
    """
    Handle /api/user and /api/user/{id}.
    """

    async def get(self, userId=None, *args, **kwargs):
        """
        :param userId: must not None
        :param args:
        :param kwargs:
        :return: user domain with out password, 200 if is this user, else domain without phoneNumber and rooms; None 404
        Validation:
        UserId is not None
        User exists in db user
        """
        try:
            if userId:
                db = self.settings["db"]
                user_repo = db.user
                result = await user_repo.find_one({"_id": ObjectId(userId)})
                if result is None:
                    raise ValueError("User id not found")
                objectIdToStr(result)
                del result["password"]
                result["rooms"] = list(map(str, result["rooms"]))
                if not await auth_with_token(self.settings["my_redis"], self.request.headers["Authorization"]):
                    del result["phoneNumber"]
                    del result["rooms"]
                self.set_status(200)
                self.write(json.dumps(result))
                return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)

    async def post(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return: user domain with out password, 201; None, 403

        Validation:
        function user_validation
        phoneNumber is unique
        """
        try:
            user = json.loads(self.request.body)
            domains.user_validation(user)
            db = self.settings["db"]
            user_repo = db.user
            if await user_repo.count_documents({"phoneNumber": user["phoneNumber"]}) > 0:
                raise ValueError("User already registered")
            user["password"] = Encryption.encryption(user["password"])
            await user_repo.insert_one(user)

            objectIdToStr(user)
            del user["password"]
            self.set_status(201)
            self.write(json.dumps(user))
            return
        except asyncio.CancelledError:
            raise
        except ValueError:
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class UserPhoneNumberHandler(BaseHandler, ABC):
    """
    Handle /api/user/phoneNumber/{phoneNumber}.
    """

    async def get(self, phoneNumber=None, *args, **kwargs):
        """
        :param phoneNumber:
        :param args:
        :param kwargs:
        :return: user domain without password: 200; None, 404
        Validation:
        phoneNumber exists in db user
        """
        try:
            if phoneNumber:
                db = self.settings["db"]
                user_repo = db.user
                result = await user_repo.find_one({"phoneNumber": phoneNumber})
                if result is None:
                    raise ValueError("User id not found")
                objectIdToStr(result)
                result["rooms"] = list(map(str, result["rooms"]))
                del result["password"]
                if not await auth_with_token(self.settings["my_redis"], self.request.headers["Authorization"]):
                    del result["phoneNumber"]
                    del result["rooms"]
                self.set_status(200)
                self.write(json.dumps(result))
                return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)


class RoomHandler(BaseHandler, ABC):
    """
    Handle /api/room and /api/{id}
    """

    async def get(self, roomId=None, *args, **kwargs):
        """
        :param roomId:
        :param args:
        :param kwargs:
        :return: room domain, 200; None, 404
        Validation:
        roomId is not None
        roomId exists in db room
        """
        try:
            if roomId:
                db = self.settings["db"]
                room_repo = db.room
                result = await room_repo.find_one({"_id": ObjectId(roomId)})
                if result is None:
                    raise ValueError("Room id not found")
                objectIdToStr(result)
                result["members"] = list(map(str, result["members"]))
                result["room_message_id"] = list(map(str, result["room_message_id"]))
                tornado.log.app_log.warning(result)
                self.set_status(200)
                self.write(json.dumps(result))
                return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)

    async def post(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return: room domain, 201; None 403
        Validation:
        function room_validation
        """
        try:
            room = json.loads(self.request.body)
            domains.room_validation(room)
            db = self.settings["db"]
            room_repo = db.room
            await room_repo.insert_one(room)
            objectIdToStr(room)
            self.set_status(201)
            self.write(json.dumps(room))
            return
        except asyncio.CancelledError:
            raise
        except ValueError:
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class RoomChangeHandler(BaseHandler, ABC):
    """
    Handle /api/room/{id}/{userId}
    """

    async def post(self, roomId, userId, *args, **kwargs):
        """
        :param roomId:
        :param userId:
        :param args:
        :param kwargs:
        :return: room domain, 201; None, 403
        Validation:
        function room_validation
        roomId and userId is not None
        roomId and userId exist in db room and user
        userId is not in members list of room item
        """
        try:
            if not await auth_with_token(self.settings["my_redis"], self.request.headers["Authorization"]):
                tornado.log.app_log.warning(self.request.headers["Authorization"])
                uid = jwt.api_jwt.decode(self.request.headers["Authorization"], key="secret",
                                         algorithms="HS256",
                                         audience="ENIGMA", iss="ENIGMA")["uid"]
                tornado.log.app_log.warning(uid)
                tornado.log.app_log.warning((await self.settings["my_redis"].get(uid)).decode())
                self.set_status(401)
                return
            if not (roomId and userId):
                raise ValueError("Missing Ids.")

            roomId = ObjectId(roomId)
            userId = ObjectId(userId)
            db = self.settings["db"]
            room_repo = db.room
            user_repo = db.user
            room_item_num = await room_repo.count_documents({"_id": roomId})
            user_item_num = await user_repo.count_documents({"_id": userId})
            if room_item_num == 0 or user_item_num == 0:
                raise ValueError("Id does not exist.")
            if await room_repo.count_documents({"_id": roomId, "members": userId}) > 0:
                raise ValueError("User already in room")
            await room_repo.update_one({"_id": roomId}, {"$push": {"members": userId}})
            await user_repo.update_one({"_id": userId}, {"$push": {"rooms": roomId}})
            self.set_status(201)
            return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class MessageHandler(BaseHandler, ABC):
    """
    Handle /api/message and /api/message/{id}
    """

    def __init__(self, application: "Application", request: httputil.HTTPServerRequest, **kwargs: Any) -> None:
        super().__init__(application, request, **kwargs)

    async def post(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return: None, 201; None, 403
        Validation:
        function message_validation
        userId and roomId exist in db user and room
        """
        try:
            if not await auth_with_token(self.settings["my_redis"], self.request.headers["Authorization"]):
                self.set_status(401)
                return
            message = json.loads(self.request.body)
            domains.message_validation(message)
            db = self.settings["db"]
            client = self.settings["client"]
            message_repo = db.message
            user_repo = db.user
            room_repo = db.room
            userId = ObjectId(message["userId"])
            roomId = ObjectId(message["roomId"])
            room_message_repo = db.room_message
            if await user_repo.count_documents({"_id": userId}) == 0 or \
                    await room_repo.count_documents({"_id": roomId}) == 0:
                raise ValueError("User or room not exists")
            update_time = int(datetime.datetime.utcnow().timestamp())
            message["create_time"] = update_time
            async with await client.start_session() as s:
                async with s.start_transaction():
                    result = await message_repo.insert_one(message, session=s)
                    messageId = result.inserted_id
                    room_repo.update_one({"_id": roomId},
                                         {"$set": {"update_time": update_time}, "$inc": {"message_num": 1}},
                                         session=s)
                    room_message_id_list = (room_repo.find_one({"_id": roomId}))["room_message_id"]
                    if len(room_message_id_list) > 0:
                        # If message already sent in this room
                        room_message_id = room_message_id_list[-1]
                        room_message_item = room_message_repo.find_one({"_id": room_message_id}, session=s)
                        if len(room_message_item["messages"]) >= self.settings["message_num_per_document"]:
                            # If message exceeds the max message num of one room message document
                            new_room_message_id = (room_message_repo.insert_one(
                                {"messages": [messageId]}, session=s)).inserted_id
                            room_repo.update_one({"_id": roomId},
                                                 {"$push": {"room_message_id": new_room_message_id}}, session=s)
                        else:
                            room_message_repo.update_one({"_id": room_message_id},
                                                         {"$push": {"messages": messageId}}, session=s)
                    else:
                        new_room_message_id = (room_message_repo.insert_one(
                            {"room_id": roomId, "messages": [messageId]}, session=s)).inserted_id
                        room_repo.update_one({"_id": roomId}, {"$push": {"room_message_id": new_room_message_id}},
                                             session=s)
            objectIdToStr(message)
            self.set_status(201)
            return
        except asyncio.CancelledError:
            raise
        except ValueError:
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class RoomMessageHandler(BaseHandler, ABC):
    """
    Handle /api/room/{roomId}/latest/{update-time}/{message-num}
    """

    async def get(self, roomId=None, update_time=None, message_num=None, *args, **kwargs):
        """
        :param update_time:
        :param roomId:
        :param message_num:
        :param args:
        :param kwargs:
        :return: list of domain message, 200; None, 404
        """
        max_num = self.settings["max_message_num_per_get"]
        try:
            if not await auth_with_token(self.settings["my_redis"], self.request.headers["Authorization"]):
                self.set_status(401)
                return
            if roomId and message_num and update_time is None:
                raise ValueError("One of argument is None.")
            db = self.settings["db"]
            room_repo = db.room
            message_repo = db.message
            room_message_repo = db.room_message
            room_item = await room_repo.find_one({"_id": ObjectId(roomId)})
            message_num_per_document = self.settings["message_num_per_document"]
            if room_item is None:
                raise ValueError("Room id not exists.")
            room_message_list = room_item["room_message_id"]
            new_update_time = int(room_item["update_time"])
            new_message_num = int(room_item["message_num"])
            update_time = int(update_time)
            message_num = int(message_num)
            if new_update_time > update_time and new_message_num < message_num:
                message_num = max_num
            elif new_update_time >= update_time and new_message_num >= message_num:
                message_num = new_message_num - message_num
                message_num = min(message_num, max_num)
            else:
                raise ValueError("Wrong update time or message num.")
            if message_num == 0:
                self.set_status(200)
                self.write(json.dumps([]))
                return
            room_message_num = math.ceil(message_num / message_num_per_document)
            room_message_fetch_list = room_message_list[-room_message_num:]
            room_message_fetch_list = list(map(ObjectId, room_message_fetch_list))
            message_id = []
            async for room_message_item in room_message_repo.find({"_id": {"$in": room_message_fetch_list}}):
                message_id.extend(room_message_item["messages"])
            cursor = message_repo.find({"_id": {"$in": message_id}}).sort("_id", pymongo.DESCENDING)
            messages = await cursor.to_list(length=message_num)
            for i in messages:
                i["_id"] = str(i["_id"])
            self.set_status(200)
            self.write(json.dumps(messages))
            return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)


class LoginHandler(BaseHandler, ABC):
    """
    Handle login and logout with session.
    """

    async def post(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return: token and userId

        Help to login and generate a token.
        """
        try:
            login = json.loads(self.request.body)
            domains.login_validation(login)
            db = self.settings["db"]
            my_redis = self.settings["my_redis"]
            user_repo = db.user
            phone_number = login["phoneNumber"]
            password = login["password"]
            user_item = await user_repo.find_one({"phoneNumber": phone_number})
            if not user_item:
                raise ValueError("User or room not exists")
            uid = str(user_item["_id"])
            true_password = user_item["password"]
            if Encryption.validation(password, true_password):
                token = token_generate(uid, 86400 * 5)
                await my_redis.set(uid, token)
                self.write(json.dumps(
                    {
                        "userId": uid,
                        "token": token
                    }
                ))
                self.set_status(201)
                return
        except asyncio.CancelledError:
            raise
        except ValueError:
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


def main():
    client = motor.motor_tornado.MotorClient()
    db = client.chatroom
    lock = asyncio.Lock()
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "xsrf_cookies": False,
    }
    my_redis = aredis.StrictRedis(host="127.0.0.1", port=6379, db=0)
    app = tornado.web.Application(
        [
            (r"/", BaseHandler),
            (r"/api/user/([0-9a-zA-z]+)", UserHandler),
            (r"/api/user/phoneNumber/([0-9]+)", UserPhoneNumberHandler),
            (r"/api/user", UserHandler),
            (r"/api/room/([0-9a-zA-z]+)/user/([0-9a-zA-z]+)", RoomChangeHandler),
            (r"/api/room/([0-9a-zA-z]+)", RoomHandler),
            (r"/api/room", RoomHandler),
            (r"/api/message", MessageHandler),
            (r"/api/room/([0-9a-zA-z]+)/latest/([0-9]+)/([0-9]+)", RoomMessageHandler),
            (r"/api/session", LoginHandler),
        ],
        db=db,
        client=client,
        message_num_per_document=100,
        max_message_num_per_get=500,
        my_lock=lock,
        my_redis=my_redis,
        debug=True,
        autoreload=True,
        **settings
    )
    app.listen(9999)
    tornado.log.app_log.warning("Server running at port {}".format(9999))
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
