import json
from abc import ABC
from typing import Optional, Awaitable, Any

import motor
import tornado.ioloop
import tornado.web
import tornado.log

from bson.objectid import ObjectId
import bson

import asyncio

from tornado import httputil

import domains
import bcrypt
import time
import math

from tornado.web import Application

"""
Author: Enigma Zhang

Description:
    This module is the main file of app which defines settings, routers and API handlers.
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


class BaseHandler(tornado.web.RequestHandler, ABC):

    def prepare(self) -> Optional[Awaitable[None]]:
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        return super().prepare()


class UserHandler(BaseHandler, ABC):
    """
    Handle /api/user and /api/user/{id}.
    """
    async def get(self, userId=None, *args, **kwargs):
        """
        :param userId: must not None
        :param args:
        :param kwargs:
        :return: user domain with out password, 200; None 404
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
                del result["password"]
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
            if await user_repo.count_documents({"_id": userId}) == 0 and \
                    await room_repo.count_documents({"_id": roomId}) == 0:
                raise ValueError("User or room not exists")
            update_time = int(time.time())
            message["create_time"] = update_time
            async with await client.start_session() as s:
                async with s.start_transaction():
                    result = await message_repo.insert_one(message, session=s)
                    messageId = result.inserted_id
                    await room_repo.update_one({"_id": roomId},
                                               {"$set": {"update_time": update_time}, "$inc": {"message_num": 1}},
                                               session=s)
                    room_message_id_list = (await room_repo.find_one({"_id": roomId}))["room_message_id"]
                    if len(room_message_id_list) > 0:
                        # If message already sent in this room
                        room_message_id = room_message_id_list[-1]
                        room_message_item = await room_message_repo.find_one({"_id": room_message_id}, session=s)
                        if len(room_message_item["messages"]) >= self.settings["message_num_per_document"]:
                            # If message exceeds the max message num of one room message document
                            new_room_message_id = (await room_message_repo.insert_one(
                                {"messages": [messageId]}, session=s)).inserted_id
                            await room_repo.update_one({"_id": roomId},
                                                       {"$push": {"room_message_id": new_room_message_id}}, session=s)
                        else:
                            await room_message_repo.update_one({"_id": room_message_id},
                                                               {"$push": {"messages": messageId}}, session=s)
                    else:
                        new_room_message_id = (await room_message_repo.insert_one(
                            {"room_id": roomId, "messages": [messageId]}, session=s)).inserted_id
                        await room_repo.update_one({"_id": roomId}, {"$push": {"room_message_id": new_room_message_id}},
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
            if new_update_time > update_time and new_message_num <= message_num:
                message_num = max_num
            elif new_update_time >= update_time and new_message_num >= message_num:
                message_num = new_message_num - message_num
                message_num = max(message_num, max_num)
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
            cursor = message_repo.find({"_id": {"$in": message_id}})
            messages = await cursor.to_list(length=max_num)
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


def main():
    client = motor.motor_tornado.MotorClient()
    db = client.chatroom
    lock = asyncio.Lock()
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
            (r"/api/room/([0-9a-zA-z]+)/latest/([0-9]+)/([0-9]+)", RoomMessageHandler)
        ],
        db=db,
        client=client,
        message_num_per_document=100,
        max_message_num_per_get=500,
        my_lock=lock,
        debug=True
    )
    app.listen(9999)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
