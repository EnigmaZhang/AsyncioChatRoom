# 域和API设计

## domain

* user: _id, name(<=32, >=1, number+letter+double byte), phoneNumber(unique)(number), password(>=8, <=32, number+letter), rooms

* room: _id, name, members, messages

* messages(in room): _id, userId, roomId, content, time

## API

### user

* post: name, phoneNumber, password

    201: domain without the password, 403: failed  

* get: /{id}

    200: domain without the password, 404: not found

* get: /phoneNumber/{phoneNumber}

    200: domain without the password, 404: not found
