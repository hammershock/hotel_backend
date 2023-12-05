import os

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import datetime


app = Flask(__name__)
CORS(app)

# 配置 JWT
app.config['JWT_SECRET_KEY'] = os.urandom(24)

jwt = JWTManager(app)


users = {
    "111客户": "111",
    "222前台": "222",
    "333管理员": "333"
}


room_status = {
        "isOn": False,
        "temperatureMin": 16,
        "temperature": 22,
        "temperatureMax": 30,
        "fanSpeed": "medium",
        "mode": "cool",
        "consumption": 0.0,
        "roomTemperature": 22,
        "rate": 0.1
    }


@app.route('/room-status/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room_status(room_id):
    """
    查询房间状态数据<READ>
    权限设置：用户只能查询自己对应的房间状态，而管理员可以查询所有的房间状态，不为前台提供这项接口
    :param room_id: 房间号
    :return:
    """
    username = get_jwt_identity()  # 查询来自的帐号名
    return jsonify(room_status)


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
    username = get_jwt_identity()  # 查询来自的帐号名
    data = request.json
    room_status.update(data)
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

    # 验证用户名和密码
    if username+role not in users or users[username+role] != password:
        return jsonify({"msg": "Bad username or password"}), 401
    # 创建 JWT token
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity=username, expires_delta=expires)
    return jsonify(token=access_token)


@app.route('/register', methods=['POST'])
@jwt_required()
def register():
    """
    注册用户帐号，传入json消息体格式如:
    {'account': {'username': 210, 'password': '666'},
    'customer': {'idCard': '124', 'phone': '124', 'roomType': '标准间', 'days': 3},
    'manager' : {这个不重要...}}
    权限设置：只有[前台，管理员]能进行此操作, 且前台只能注册客户帐号
    :return:
    """
    data = request.json
    username = get_jwt_identity()
    return jsonify({"msg": "注册成功"}), 201


if __name__ == '__main__':
    app.run(debug=True)
