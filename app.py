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

# 假设的用户数据
users = {
    "111客户": "111",
    "222前台": "222",
    "333管理员": "333"
    # ... 其他用户 ...
}


room_status = {
        "isOn": False,
        "temperatureMin": 16,
        "temperature": 22,
        "temperatureMax": 30,
        "fanSpeed": "medium",
        "mode": "cool",
        "consumption": 0.2,
        "roomTemperature": 22,
        "rate": 0.1
    }


@app.route('/some-protected-route')
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    # 你现在知道了请求是由谁发出的
    return jsonify(logged_in_as=current_user), 200


@app.route('/room-status/<int:room_id>', methods=['GET'])
@jwt_required()
def get_room_status(room_id):
    # 这里可以添加逻辑来根据 room_id 获取实际的房间状态
    # 目前我们只是返回假设的数据
    global ison
    current_user = get_jwt_identity()
    # print(room_id, current_user)
    return jsonify(room_status)


@app.route('/update-status/<int:room_id>', methods=['POST'])
@jwt_required()
def update_status(room_id):
    current_user = get_jwt_identity()
    data = request.json
    room_status.update(data)

    print(data, current_user)
    # 更新房间状态的逻辑...
    return jsonify({"msg": "状态更新成功"}), 200


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    role = request.json.get('role', None)

    # print(username, password)
    # 验证用户名和密码
    if username+role not in users or users[username+role] != password:
        return jsonify({"msg": "Bad username or password"}), 401
    # 创建 JWT token
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity=username, expires_delta=expires)
    # print(role, username, password, access_token)
    return jsonify(token=access_token)


if __name__ == '__main__':
    app.run(debug=True)


def hello_world():  # put application's code here
    return 'Hello World!'

