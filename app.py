import os

from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from flask_cors import CORS
import datetime

app = Flask(__name__)
CORS(app)

# 配置 JWT
app.config['JWT_SECRET_KEY'] = secret_key = os.urandom(24)  # Change this!
print("secret_key", secret_key)

jwt = JWTManager(app)

# 假设的用户数据
users = {
    "111": "11",
    "222": "122"
    # ... 其他用户 ...
}


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    print(username, password)
    # 验证用户名和密码
    if username not in users or users[username] != password:
        return jsonify({"msg": "Bad username or password"}), 401

    # 创建 JWT token
    expires = datetime.timedelta(days=7)
    access_token = create_access_token(identity=username, expires_delta=expires)

    return jsonify(access_token=access_token)


if __name__ == '__main__':
    app.run(debug=True)


def hello_world():  # put application's code here
    return 'Hello World!'

