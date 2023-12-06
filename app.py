import os
import random

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import datetime

import database.roles
from database.roles import manager, customer
from database import room, account, record, settings

app = Flask(__name__)
CORS(app)

# 配置 JWT
app.config['JWT_SECRET_KEY'] = os.urandom(24)

jwt = JWTManager(app)


def get_time_stamp() -> str:
    current_time = datetime.datetime.now()
    timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp_str


def generate_customer_session_id() -> int:
    """
    生成一个用于 customer_session_id 的随机整数
    :return: 随机生成的 customer_session_id
    """
    # 生成一个随机整数，这里的范围可以根据需要调整
    session_id = random.randint(0, 999999)
    return session_id


@app.route('/room-status/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room_status(room_id):
    """
    查询房间状态数据<READ>
    权限设置：用户只能查询自己对应的房间状态，而管理员可以查询所有的房间状态，不为前台提供这项接口
    :param room_id: 房间号
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    if acc is None:
        return jsonify({}), 401  # 未授权

    role = acc[3]  # 判断查询的是什么角色

    if role == manager:
        room_status = room.query(fetchone=True, room_number=room_id)  # 总经理可以查询任意id

    elif role == customer:
        room_status = room.query(account_id=account_id, fetchone=True)  # 根据客户自己的房间ID来查找，不论客户查询什么房间都返回其自己的房间信息
    else:
        room_status = None

    if room_status is None:
        return jsonify({}), 404  # Not Found

    room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id = room_status

    _, _, min_temperature, max_temperature, ac_rate = settings.get_latest_setting(ac_speed, ac_mode)
    return jsonify(
        {'isOn': ac_is_on, 'temperature': ac_temperature, 'fanSpeed': ac_speed,
         'mode': ac_mode, 'consumption': room_consumption, 'roomTemperature': room_temperature,
         'rate': ac_rate, 'temperatureMin': min_temperature, 'temperatureMax': max_temperature}), 200


@app.route('/update-status/<int:room_id>', methods=['POST'])
@jwt_required()
def update_status(room_id):
    """
    修改房间状态数据<WRITE>
    权限设置：用户只能修改自己对应的房间状态，而管理员可以修改所有的房间状态，不为前台提供这项接口
    前置条件：房间号必须存在，修改状态合法
    后置条件：房间状态已修改
    :param room_id: 房间号
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    data = request.json

    room.update(room_number=room_id, ac_is_on=data['isOn'], ac_temperature=data['temperature'], ac_speed=data['fanSpeed'], ac_mode=data['mode'])
    room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id = room.query(room_number=room_id, fetchone=True)
    print(ac_speed, ac_mode)
    _, _, _, _, ac_rate = settings.get_latest_setting(ac_speed, ac_mode)
    record.add(room_number=room_id, customer_session_id=generate_customer_session_id(), room_temperature=room_temperature, timestamp=get_time_stamp(), ac_is_on=ac_is_on, ac_temperature=ac_temperature, ac_speed=ac_speed, ac_mode=ac_mode, ac_rate=ac_rate)

    return jsonify({"msg": "状态更新成功"}), 200


@app.route('/login', methods=['POST'])
def login():
    """
    用户、前台、管理员的登录
    <唯一不需要token的操作接口>
    :return:
    """
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    role = request.json.get('role', None)
    # tables = account.print_tables()
    acc = account.query(username=username, role=role, password=password, fetchone=True)
    if acc is None:
        return jsonify({"msg": "Bad username or password"}), 401
    # 创建 JWT token
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity=acc[0], expires_delta=expires)
    return jsonify(token=access_token)


@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    登出，这部分逻辑是冗余的，因为JWT token不需要也不能进行销毁，它们到时间会自动过期
    在这里仅仅是为了前后呼应233
    :return:
    """
    return jsonify({"msg": "登出成功"}), 200


@app.route('/register', methods=['POST'])
@jwt_required()
def register():
    """
    注册用户帐号，传入json消息体格式如:
    {'account': {'username': 210, 'password': '666', role: 'customer'},
    'customer': {'idCard': '124', 'phone': '124', 'roomType': '标准间', 'days': 3},
    'manager' : {这个不重要...}}
    权限设置：只有[前台，管理员]能进行此操作, 且前台只能注册客户帐号
    :return:
    """
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    try:
        # data:
        # username: this.selectedRoom,
        # password: this.account.password,
        #
        # idCard: this.customer.idCard,
        # phone: this.customer.phone,
        # roomType: this.customer.roomType,
        # days: this.customer.days

        # role: ...
        if role == database.roles.front_desk:
            room_exists = room.query(room_number=int(data['username']), fetchone=True) is not None
            if room_exists:
                new_account_id = account.create(data['username'], database.roles.customer, data['password'],
                                                data['idCard'], data['phone'])
                room.update(room_number=int(data['username']),
                            room_duration=data['days'],
                            room_consumption=0.0,
                            account_id=new_account_id,
                            customer_session_id=generate_customer_session_id())

                return jsonify({"msg": "注册成功", "new_account_id": new_account_id}), 201
            return jsonify({"msg": ""}), 404

        elif role == database.roles.manager:
            new_account_id = account.create(data['username'], data['role'], data['password'], data['idCard'], data['phone'])
            return jsonify({"msg": "注册成功", 'new_account_id': new_account_id}), 201
    except Exception as e:
        print(e)
    return jsonify({"msg": ""}), 401


@app.route('/delete-account', methods=['POST'])
@jwt_required()
def delete_account():
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    if role == database.roles.manager:
        account.delete(username=data['username'], role=data['role'])
        return jsonify({"msg": "注销成功"}), 201

    return jsonify({"msg": ""}), 404


@app.route('/delete-room', methods=['POST'])
@jwt_required()
def delete_room():
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        room.delete(room_number=data['roomID'])
        return jsonify({"msg": "注销成功"}), 201

    return jsonify({"msg": ""}), 404


@app.route('/rooms-available', methods=['GET'])
@jwt_required()
def get_rooms_available():
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.front_desk:
        rooms = room.query(fetchall=True)
        return jsonify([{'number': r[0], "occupied": r[1] is not None} for r in rooms]), 200

    return jsonify({"msg": ""}), 404


@app.route('/rooms-state', methods=['GET'])
@jwt_required()
def get_rooms_state():
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    if role == database.roles.manager:
        rooms = room.query(fetchall=True)
        return jsonify([{'roomNumber': r[0],
                         "occupied": r[1] is not None,
                         "type": r[2],
                         "duration": r[3],
                         "consumption": r[4],
                         "roomTemperature": r[5],
                         "acIsOn": r[6],
                         "acTemperature": r[7],
                         "acSpeed": r[8],
                         "acMode": r[9],
                         "customerSessionID": r[10]} for r in rooms]), 200

    return jsonify({"msg": ""}), 404



@app.route('/view-accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    if role == database.roles.manager:
        accounts = account.query(fetchall=True)
        # account_id, username, password, role, id_card, phone_number
        return jsonify([{'accountID': r[0], "username": r[1], "role": r[3], "idCard": r[4], "phoneNumber": r[5]} for r in accounts]), 200

    return jsonify({"msg": ""}), 404


@app.route('/view-rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        rooms = room.query(fetchall=True)
        # room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id
        return jsonify([{'id': r[0], "type": r[2], "days": r[3], "consumption": r[4]} for r in rooms]), 200

    return jsonify({"msg": ""}), 404


if __name__ == '__main__':
    app.run(debug=True)

