import os

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import datetime


app = Flask(__name__)
CORS(app)

# 配置 JWT
app.config['JWT_SECRET_KEY'] = secret_key = os.urandom(24)
print("secret_key", secret_key)

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
    username = get_jwt_identity()  # 查询来自的帐号名
    return jsonify(room_status)


@app.route('/update-status/<int:room_id>', methods=['POST'])
@jwt_required()
def update_status(room_id):
    username = get_jwt_identity()  # 查询来自的帐号名
    data = request.json
    room_status.update(data)
    return jsonify({"msg": "状态更新成功"}), 200


@app.route('/login', methods=['POST'])
def login():
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
    data = request.json
    username = get_jwt_identity()
    # {'account': {'username': 210, 'password': '666'},
    # 'customer': {'idCard': '124', 'phone': '124', 'roomType': '标准间', 'days': 3}}
    return jsonify({"msg": "注册成功"}), 201


if __name__ == '__main__':
    app.run(debug=True)
