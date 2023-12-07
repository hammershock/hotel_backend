import os
import random

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import datetime

import database.roles

from database import room, account, record, settings
from database.roles import *

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


@app.route('/update-status', methods=['POST'])
@app.route('/update-status/<int:room_id>', methods=['POST'])
@jwt_required()
def update_status(room_id=None):
    """
    写入房间状态数据<WRITE>
    # data
        # isOn
        # temperature
        # fanSpeed
        # mode
        # roomType (可选，只有管理员可以修改这个)
        # roomDuration　(可选，只有管理员可以修改)

        # 不提供给管理员修改房间总消费额和房间温度的API
    :param room_id: 房间号 (不填则根据客户信息自动导航)
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号名
    account_data = account.query(account_id=account_id, fetchone=True)
    role = account_data[3]
    data = request.json

    if role == database.roles.customer:  # 自动跳转到用户自己的房间号
        room_id = account_data[4]
    print(room_id)
    # 检查房间是否存在
    room_data = room.query(room_number=room_id, fetchone=True)

    if room_data is None:
        return jsonify({"msg": 'room not found'}), 404

    (room_number, account_id, room_type, room_duration, room_consumption, room_temperature,
     ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id) = room_data

    is_manager = role == database.roles.manager
    # 检验修改是否合法
    # ...
    # 修改房间状态
    room.update(room_number=room_id,
                room_type=data.get('roomType', None) if is_manager else None,
                room_duration=data.get('roomDuration', None) if is_manager else None,
                ac_is_on=data['isOn'],
                ac_temperature=data['temperature'],
                ac_speed=data['fanSpeed'],
                ac_mode=data['mode'],
                )

    _, _, _, _, ac_rate = settings.get_latest_setting(ac_speed, ac_mode)

    record.add(room_number=room_id,
               customer_session_id=customer_session_id,
               room_temperature=room_temperature,
               timestamp=get_time_stamp(),
               ac_is_on=ac_is_on,
               ac_temperature=ac_temperature,
               ac_speed=ac_speed,
               ac_mode=ac_mode,
               ac_rate=ac_rate)

    return jsonify({"msg": "状态更新成功"}), 200


@app.route('/login', methods=['POST'])
def login():
    """
    用户、前台、管理员的登录
    <唯一不需要token的操作接口>
    # data
        # username
        # password
        # role  # 在'客户', '管理员', '前台'中指定

    :return:
    """
    try:
        data = request.json
        username = data['username']
        password = data['password']
        role = data['role']

        account_data = account.query(username=username, role=role, password=password, fetchone=True)

        if account_data is None:
            return jsonify({"msg": "Bad username or password"}), 401  # 401 Unauthorized

        # 创建 JWT token
        expires = datetime.timedelta(days=7)
        access_token = create_access_token(identity=account_data[0], expires_delta=expires)
        return jsonify(token=access_token), 200  # 200 ok
    except KeyError as e:
        return jsonify({"msg": e}), 400  # 400 bad request 请求格式不正确
    # 500 server error


@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    使用JWT token 进行验证
    不需要登出操作
    服务端不需要维护登录态
    :return:
    """
    raise NotImplementedError


@app.route('/register', methods=['POST'])
@jwt_required()
def register():
    """
    注册用户帐号，传入json消息体格式如:
    # data:
        # username: this.selectedRoom,
        # password: this.account.password,
        # roomNumber: this.account.roomNumber
        # days: this.customer.days
        # idCard: this.customer.idCard,  # (可选)
        # phone: this.customer.phone,　　# (可选)

    权限设置：只有[前台，管理员]能进行此操作
    :return:
    """
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    if role not in {database.roles.front_desk, database.roles.manager}:
        return jsonify({"msg": ""}), 403  # Forbidden

    try:
        room_data = room.query(room_number=data['roomNumber'], fetchone=True)
        if room_data is None or room_data[1] is not None:
            return jsonify({"msg": "房间不存在或已被占用"}), 404  # 404 NotFound

        new_account_id = account.create(data['username'],
                                        database.roles.customer,  # 通过登记方法注册的一定是客户帐号
                                        data['password'],
                                        data['roomNumber'],  # 登记用户时，其对应的房间是必选的项
                                        data.get('idCard', None),
                                        data.get('phone', None))

        room.update(room_number=data['roomNumber'],
                    room_duration=data['days'],
                    room_consumption=0.0,  # 初始化房间累计消费额为0
                    account_id=new_account_id,  # 将创建的用户id与房间关联
                    customer_session_id=generate_customer_session_id())  # 生成随机用户会话标记，标记每个用户的入住阶段

        return jsonify({"msg": "注册成功", "newAccountID": new_account_id}), 201

    except KeyError as e:
        return jsonify({"msg": e}), 400  # 400 bad request 请求格式不正确
    # 500, 服务器错误


@app.route('/check-out', methods=['POST'])
@jwt_required()
def signout():
    """
    用户办理退房:
    json消息体可以包含：
    # data
        # roomNumber  (二者任选其一)
        # username  (二者任选其一)
    :return:
    """

    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色
    if role not in {database.roles.front_desk, database.roles.manager}:
        return jsonify({"msg": ""}), 403  # Forbidden

    if data.get('roomNumber') is None:
        username = data['username']
        acc = account.query(username=username, role=database.roles.customer, fetchone=True)
        room_number = acc[4]
    else:
        room_number = data['roomNumber']
        customer_account_id = room.query(room_number=room_number, fetchone=True)[1]
        acc = account.query(customer_account_id, fetchone=True)
        if acc is None:
            return jsonify({"msg": "房间不存在或已被清空"}), 404  # 404 NotFound
        username = acc[1]

    try:
        room_data = room.query(room_number=room_number, fetchone=True)
        if room_data is None or room_data[1] is None:
            return jsonify({"msg": "房间不存在或已被清空"}), 404  # 404 NotFound

        account.delete(username, database.roles.customer)
        room.update_kwargs(room_number, room_duration=0, room_consumption=0.0, ac_is_on=False, customer_session_id=None, account_id=None)

        return jsonify({"msg": "退房成功"}), 201

    except KeyError as e:
        return jsonify({"msg": e}), 400  # 400 bad request 请求格式不正确


@app.route('/delete-account', methods=['POST'])
@jwt_required()
def delete_account():
    """
    删除任何一个帐号只需要用户名即可，但只有管理员有权限
    # data
        # username
    :return:
    """
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    account_data = account.query(account_id=account_id, fetchone=True)
    role = account_data[3]  # 判断查询的是什么角色
    if role == database.roles.manager:
        account.delete(username=data['username'], role=data['role'])
        return jsonify({"msg": "注销成功"}), 201

    return jsonify({"msg": ""}), 404


@app.route('/create-account', methods=['POST'])
@jwt_required()
def create_account():
    """
    创建帐号是管理员能做的事情，与register区分开
    不建议使用此方法创建客户帐号，建议走register流程

    # data
        # username
        # password
        # role # 在'客户', '管理员', '前台'中指定， 必选
        # idCard (可选)
        # phoneNumber (可选)
        # roomNumber (可选，注册管理帐号不一定与房间挂钩)
    :return:
    """
    data = request.json
    # { username: '', password: '', role: '', idCard: '', phoneNumber: '', roomNumber: ''}
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        room_number = data.get('roomNumber')
        if room_number:
            room_data = room.query(room_number=data['roomNumber'], fetchone=True)
            if room_data is None or room_data[1] is not None:
                return jsonify({"msg": "房间不存在或已被占用"}), 404  # 404 NotFound
            account_id = account.create(username=data['username'],
                           role=data['role'],
                           password=data['password'],
                           room_number=data.get('roomNumber', None),
                           id_card=data['idCard'],
                           phone_number=data['phoneNumber'])

            room.update(room_number, room_duration=data['days'], room_consumption=0.0, customer_session_id=generate_customer_session_id(), account_id=account_id)
            return jsonify({"msg": "用户帐号已经注册且入住已经办理"}), 201

        account.create(username=data['username'],
                       role=data['role'],
                       password=data['password'],
                       room_number=data.get('roomNumber', None),
                       id_card=data['idCard'],
                       phone_number=data['phoneNumber'])
        return jsonify({"msg": "创建成功"}), 201

    return jsonify({"msg": ""}), 404


@app.route('/create-room', methods=['POST'])
@jwt_required()
def create_room():
    """
    创建新房间是管理员特有的权限

    # data
        # roomNumber
        # roomType
        # role # 在'客户', '管理员', '前台'中指定， 必选
        # idCard (可选)
        # phoneNumber (可选)
        # roomNumber (可选，注册管理帐号不一定与房间挂钩)
    :return:
    """
    data = request.json
    #
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        room.create(room_number=data['roomNumber'],
                    room_type=data['roomType'],
                    room_duration=0,  # 设置为0
                    room_consumption=0.0,  # 初始消费为0
                    room_temperature=random.randint(27, 34),  # 初始温度随机
                    ac_is_on=False,
                    ac_temperature=DEFAULT_AC_TEMPERATURE,
                    ac_speed=AC_SPEED_LOW,
                    ac_mode=AC_MODE_COOL,
                    customer_session_id=generate_customer_session_id(),
                    account_id=None)  # 帐号关联为空

        return jsonify({"msg": "创建成功"}), 201
    return jsonify({"msg": ""}), 404


@app.route('/delete-room', methods=['POST'])
@jwt_required()
def delete_room():
    """
    删除房间，只需要房间号，只有管理员有权限
    # data
        # roomID
    :return:
    """
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        room.delete(room_number=data['roomID'])
        return jsonify({"msg": "注销成功"}), 201

    return jsonify({"msg": ""}), 404


@app.route('/change-settings', methods=['POST'])
@jwt_required()
def change_settings():
    """
    更改空调设置
    # data
        # minTemperature
        # maxTemperature
        # acMode
        # acSpeed
        # acRate
    :return:
    """
    data = request.json
    account_id = get_jwt_identity()  # 查询来自的帐号id
    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        settings.create(timestamp=get_time_stamp(),
                        min_temperature=data['minTemperature'],
                        max_temperature=data['maxTemperature'],
                        ac_rate=data['acRate'],
                        ac_speed=data['acSpeed'],
                        ac_mode=data['acMode'])
        return jsonify({"msg": "更改成功"}), 201

    return jsonify({"msg": ""}), 404


# -------------------------------------------------------GET-----------------------------------------------------------

@app.route('/room-status', methods=['GET'])
@app.route('/room-status/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room_status(room_id=None):
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

    if role == database.roles.manager:
        room_status = room.query(fetchone=True, room_number=room_id)  # 总经理可以查询任意id
    elif role == database.roles.customer:
        room_status = room.query(account_id=account_id, fetchone=True)  # 根据客户自己的房间ID来查找，不论客户查询什么房间都返回其自己的房间信息
    else:
        room_status = None

    if room_status is None:
        return jsonify({}), 403  # Forbidden

    (room_number, account_id, room_type, room_duration, room_consumption, room_temperature,
     ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id) = room_status

    _, _, min_temperature, max_temperature, ac_rate = settings.get_latest_setting(ac_speed, ac_mode)

    return jsonify(
        {'isOn': ac_is_on,
         'acTemperature': ac_temperature,
         'fanSpeed': ac_speed,
         'mode': ac_mode,
         'consumption': room_consumption,
         'roomTemperature': room_temperature,
         'rate': ac_rate,
         'temperatureMin': min_temperature,
         'temperatureMax': max_temperature}), 200


@app.route('/rooms-available', methods=['GET'])
@jwt_required()
def get_rooms_available():
    """
    获取所有房间的可用状态：提供给前台使用
    返回所有房间号和是否已入住(occupied)
    [{'number': int, "occupied": bool}, ...]
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.front_desk or role == database.roles.manager:
        rooms = room.query(fetchall=True)
        return jsonify([{'number': r[0], "occupied": r[1] is not None} for r in rooms]), 200

    return jsonify({"msg": ""}), 404


# @app.route('/rooms-state', methods=['GET'])
# @jwt_required()
# def get_rooms_state():
#     """
#     获取所有房间的状态，给管理员可视化使用
#
#     :return:
#     """
#     account_id = get_jwt_identity()  # 查询来自的帐号名
#
#     acc = account.query(account_id=account_id, fetchone=True)
#     role = acc[3]  # 判断查询的是什么角色
#     if role == database.roles.manager:
#         rooms = room.query(fetchall=True)
#         return jsonify([{'roomNumber': r[0],
#                          "occupied": r[1] is not None,
#                          "type": r[2],
#                          "duration": r[3],
#                          "consumption": r[4],
#                          "roomTemperature": r[5],
#                          "acIsOn": r[6],
#                          "acTemperature": r[7],
#                          "acSpeed": r[8],
#                          "acMode": r[9],
#                          "customerSessionID": r[10]} for r in rooms]), 200
#
#     return jsonify({"msg": ""}), 404


@app.route('/view-accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    """
    查询所有帐号的信息，给管理员使用
    (不过还是不会给密码的啦)
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    if acc is None:
        return jsonify({"msg": ""}), 424

    role = acc[3]  # 判断查询的是什么角色
    if role == database.roles.manager:
        accounts = account.query(fetchall=True)
        # account_id, username, password, role, room_number, id_card, phone_number
        return jsonify([{'accountID': r[0], "username": r[1], "role": r[3], "roomNumber": r[4], "idCard": r[5], "phoneNumber": r[6]} for r in accounts]), 200

    return jsonify({"msg": ""}), 404


@app.route('/view-rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    """
    给管理员用来查看所有房间状态，
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号名

    acc = account.query(account_id=account_id, fetchone=True)
    role = acc[3]  # 判断查询的是什么角色

    if role == database.roles.manager:
        rooms = room.query(fetchall=True)
        # room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id
        return jsonify([{'id': r[0],
                         'occupied': r[1] is not None,
                         "type": r[2],
                         "duration": r[3],
                         "consumption": r[4],
                         'roomTemperature': r[5],
                         'acIsOn': r[6],
                         'acTemperature': r[7],
                         'acSpeed': r[8],
                         'acMode': r[9]
                         } for r in rooms]), 200

    return jsonify({"msg": ""}), 404


@app.route('/room-details', methods=['GET'])
@app.route('/room-details/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room_details(room_id=None):
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

    if role == database.roles.manager:
        room_details = record.query(room_number=room_id)  # 总经理可以查询任意id

    elif role == database.roles.customer:
        room_id = acc[4]
        room_details = record.query(room_number=room_id,   # 根据客户自己的房间ID来查找，不论客户查询什么房间都返回其自己的房间信息
                                    customer_session_id=record.get_latest_customer_session_id(room_id))
    else:
        room_details = None

    if room_details is None:
        return jsonify({}), 403  # Forbidden

    if len(room_details) == 0:
        return jsonify({'msg': 'found nothing'}), 404
    print(room_details)
    return jsonify({'roomDetails': room_details}), 200


if __name__ == '__main__':
    app.run(port=5000)  # host='0.0.0.0',



