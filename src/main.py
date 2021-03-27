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


def objectIdToStr(d):
    d["_id"] = str(d["_id"])


class Encryption:
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
        except asyncio.CancelledError:
            raise
        except ValueError:
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(403)


class UserPhoneNumberHandler(BaseHandler, ABC):

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
        except asyncio.CancelledError:
            raise
        except (bson.errors.InvalidId, ValueError):
            tornado.log.app_log.warning("API using error: ", exc_info=True)

        self.set_status(404)


class RoomHandler(BaseHandler, ABC):
    async def post(self, *args, **kwargs):
        room = json.loads(self.request.body)
        db = self.settings["db"]
        room_repo = db.room
        # Insert ObjectId in the room dict
        await room_repo.insert_one(room)
        objectIdToStr(room)
        self.set_status(201)
        self.write(json.dumps(room))


class MessageHandler(BaseHandler, ABC):
    async def post(self, *args, **kwargs):
        x = json.loads(self.request.body)
        return None


def main():
    db = motor.motor_tornado.MotorClient().chatroom
    app = tornado.web.Application(
        [
            (r"/", BaseHandler),
            (r"/api/user", UserHandler),
            (r"/api/user/([0-9a-zA-z]+)", UserHandler),
            (r"/api/user/phoneNumber/([0-9]+)", UserPhoneNumberHandler),
            (r"/api/message", MessageHandler),
            (r"/api/room", RoomHandler)
        ],
        db=db,
        debug=True
    )
    app.listen(9999)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
