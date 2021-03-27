import json
from abc import ABC
from typing import Optional, Awaitable

import motor
import tornado.ioloop
import tornado.web
import tornado.log

from bson.objectid import ObjectId
import bson

import asyncio
import domains
import bcrypt

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
        try:
            if userId:
                db = self.settings["db"]
                user_repo = db.user
                result = await user_repo.find_one({"_id": ObjectId(userId)})
                if result is None:
                    raise ValueError("User id not found")
                objectIdToStr(result)
                del result["password"]
                self.set_status(201)
                self.write(json.dumps(result))
                return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)

    async def post(self, *args, **kwargs):
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
        try:
            if phoneNumber:
                db = self.settings["db"]
                user_repo = db.user
                result = await user_repo.find_one({"phoneNumber": phoneNumber})
                if result is None:
                    raise ValueError("User id not found")
                objectIdToStr(result)
                del result["password"]
                self.set_status(201)
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
        try:
            if roomId:
                db = self.settings["db"]
                user_repo = db.room
                result = await user_repo.find_one({"_id": ObjectId(roomId)})
                if result is None:
                    raise ValueError("Room id not found")
                objectIdToStr(result)
                self.set_status(201)
                self.write(json.dumps(result))
                return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)

    async def post(self, *args, **kwargs):
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
        try:
            if not (roomId and userId):
                raise ValueError("Missing Ids.")

            roomId = ObjectId(roomId)
            userId = ObjectId(userId)
            db = self.settings["db"]
            room_repo = db.room
            user_repo = db.user
            room_item = await room_repo.find_one({"_id": roomId})
            user_item = await user_repo.find_one({"_id": userId})
            if not (room_item and user_item):
                raise ValueError("Id does not exist.")
            members = room_item["members"]
            rooms = user_item["rooms"]
            if userId in members:
                raise ValueError("User already in room")
            members.append(userId)
            rooms.append(roomId)
            await room_repo.update_one({"_id": roomId}, {"$set": {"members": members}})
            await user_repo.update_one({"_id": userId}, {"$set": {"rooms": rooms}})
            self.set_status(201)
            return
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class MessageHandler(BaseHandler, ABC):
    async def post(self, *args, **kwargs):
        x = json.loads(self.request.body)
        return None


def main():
    db = motor.motor_tornado.MotorClient().chatroom
    app = tornado.web.Application(
        [
            (r"/", BaseHandler),
            (r"/api/user/([0-9a-zA-z]+)", UserHandler),
            (r"/api/user/phoneNumber/([0-9]+)", UserPhoneNumberHandler),
            (r"/api/user", UserHandler),
            (r"/api/room/([0-9a-zA-z]+)/([0-9a-zA-z]+)", RoomChangeHandler),
            (r"/api/room/([0-9a-zA-z]+)", RoomHandler),
            (r"/api/room", RoomHandler),
            (r"/api/message", MessageHandler),
        ],
        db=db,
        debug=True
    )
    app.listen(9999)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
