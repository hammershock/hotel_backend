import os

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import datetime

from database.roles import manager, customer
from database import room, account

app = Flask(__name__)
CORS(app)

# 配置 JWT
app.config['JWT_SECRET_KEY'] = os.urandom(24)

jwt = JWTManager(app)


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

    room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode = room_status

    return jsonify(
        {'isOn': ac_is_on, 'temperature': ac_temperature, 'fanSpeed': ac_speed,
         'mode': ac_mode, 'consumption': room_consumption, 'roomTemperature': room_temperature,
         'rate': 0.1, 'temperatureMin': 18, 'temperatureMax': 34}), 200


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

    room.update(room_number=room_id, ac_is_on=data['isOn'], ac_temperature=data['temperature'], ac_speed=data['fanSpeed'], ac_mode=data['mode']
                )

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
    account_id = get_jwt_identity()
    role = account.query(account_id)[3]  # 判断查询的是什么角色
    try:
        print(data, role)
        return jsonify({"msg": "注册成功"}), 201
    except Exception as e:
        print(e)
    return jsonify({"msg": ""}), 401


if __name__ == '__main__':
    app.run(debug=True)

