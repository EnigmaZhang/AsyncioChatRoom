# 域和API设计

## domain

* user: _id, name(<=32, >=1, number+letter+double byte), phoneNumber(unique)(number), password(>=8, <=32, number+letter), rooms(_id)

* room: _id, name(<=32, >=1, number+letter+double byte), members(_id), message_num(number), room_message_id(_id), update_time

* room_message:_id, messages(_ids)

* messages: _id, userId, roomId, message_type, content, create_time

## API

### user

* post: name, phoneNumber, password

    201: domain without the password, 403: failed  

* get: /{id}

    200: domain without the password, 404: not found

* get: /phoneNumber/{phoneNumber}

    200: domain without the password, 404: not found

### room

* post: name, members, room_message_id, message_num

    201: domain, 403: failed

* post: /{roomId}/user/userId

    201: None, 403: failed

* get: /{id}

    200: domain, 404: not found

* get: /{roomId}/message/latest/{update-time}/{message-num}

    200: a list of message domain, 404: not found

### message

* post: userId, roomId, message_type, content, roomMessageId([])

    201: domain 403: failed

* get: /room/{roomId}/latest/{update-time}/{message-num}
  
    200: a list of message, 404: not found

### session

* post: phoneNumber, password
  
  201: userId, token, userId 401: unauthorized
