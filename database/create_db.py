import os
import sqlite3


db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../hotel.db'))


# 创建或连接到数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()


# 创建account账号表
# account_id, username, password, role, id_card, phone_number
cursor.execute('''
CREATE TABLE IF NOT EXISTS account (
    account_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    id_card TEXT,  -- 可选字段
    phone_number TEXT  -- 可选字段
)
''')


# 创建房间表
# room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode
cursor.execute('''
CREATE TABLE IF NOT EXISTS room (
    room_number INTEGER PRIMARY KEY,
    account_id INTEGER,  -- 可选的外键
    room_type TEXT,
    room_duration INTEGER,
    room_consumption REAL,
    room_temperature REAL,
    ac_is_on BOOLEAN,
    ac_temperature INTEGER,
    ac_speed TEXT,
    ac_mode TEXT,
    FOREIGN KEY (account_id) REFERENCES account (account_id) ON DELETE SET NULL
)
''')

# 修改room_records详单记录表
# record_id, room_number, customer_session_id, room_temperature, timestamp, ac_is_on, ac_temperature, ac_speed, ac_mode, ac_rate
cursor.execute('''
CREATE TABLE IF NOT EXISTS room_records (
    record_id INTEGER PRIMARY KEY,
    room_number INTEGER,
    customer_session_id INTEGER,
    room_temperature REAL,
    timestamp TEXT,  -- ISO8601 格式的日期时间字符串

    ac_is_on BOOLEAN,
    ac_temperature INTEGER,
    ac_speed TEXT,
    ac_mode TEXT,
    ac_rate REAL
)
''')

# 提交更改并关闭数据库连接
conn.commit()
conn.close()


# conn = sqlite3.connect(db_path)
# cursor = conn.cursor()
#
# cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
# tables = cursor.fetchall()
# conn.close()
# print(tables)

# idx = account_create(username='111', password='111', role='customer')
# account_create(username='222', password='222', role='manager')
# account_create(username='333', password='333', role='front-desk')
#
# room_create(idx, 111, '大床房', 1, 0.0, '', False, 28, 'low', 'heating', 32.1)
# customer_create(idx, '666666', '333333')

