# 域和API设计

## domain

* user: _id, name(<=32, >=1, number+letter+double byte), phoneNumber(unique)(number), password(>=8, <=32, number+letter), rooms(_id)

* room: _id, name(<=32, >=1, number+letter+double byte), members(_id), messages(_id), message_num(number)

* messages(in room): _id, userId, roomId, type, content, time

## API

### user

* post: name, phoneNumber, password

    201: domain without the password, 403: failed  

* get: /{id}

    200: domain without the password, 404: not found

* get: /phoneNumber/{phoneNumber}

    200: domain without the password, 404: not found

### room

* post: name, members, messages, message_num

    201: domain, 403: failed

* get: /{id}

    200: domain, 404: not found

* post: /{roomId} userId

    201: None, 403: failed
