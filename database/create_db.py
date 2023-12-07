import os
import random
import sqlite3
from datetime import datetime
from itertools import product

from database import account, room, settings

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
    room_number INTEGER, -- 可选字段
    id_card TEXT,  -- 可选字段
    phone_number TEXT  -- 可选字段
)
''')


# 创建房间表
# room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id
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
    customer_session_id INTEGER,
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
    ac_rate REAL, 
    consumption REAL
)
''')

# 创建 settings 表
# setting_id, timestamp, min_temperature, max_temperature, ac_rate, ac_speed, ac_mode
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
    setting_id INTEGER PRIMARY KEY,
    timestamp TEXT,
    min_temperature INTEGER,
    max_temperature INTEGER,
    ac_rate REAL,
    ac_speed TEXT,
    ac_mode TEXT
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

def generate_customer_session_id() -> int:
    """
    生成一个用于 customer_session_id 的随机整数
    :return: 随机生成的 customer_session_id
    """
    # 生成一个随机整数，这里的范围可以根据需要调整
    session_id = random.randint(1, 99999)
    return session_id


account.create('110b', '客户', '110b', 1101, '111', '233')
account.create('110e', '客户', '110e', 1102, '222', '666')
account.create('110f', '客户', '110f', 1103, '333', '233')
account.create('110g', '客户', '110g', 1104, '444', '666')
account.create('110f2', '客户', '110f2', 1105, '655566', '233')

account.create('222', '管理员', '222', None, '777', '724')
account.create('333', '前台', '333', None, '999', '634')

room.create(1101, '大床房', 0, 0.0, 10.0, True, 22, 'medium', 'heat', generate_customer_session_id(), None)
room.create(1102, '大床房', 0, 0.0, 15.0, True, 22, 'medium', 'heat', generate_customer_session_id(), None)
room.create(1103, '标准间', 0, 0.0, 18.0, True, 22, 'medium', 'heat', generate_customer_session_id(), None)
room.create(1104, '大床房', 0, 0.0, 12.0, True, 22, 'medium', 'heat', generate_customer_session_id(), None)
room.create(1105, '标准间', 0, 0.0, 14.0, True, 22, 'medium', 'heat', generate_customer_session_id(), None)


def get_time_stamp() -> str:
    current_time = datetime.now()
    timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp_str


from database.roles import *
from decimal import Decimal


settings.create(get_time_stamp(), 18, 25, 1, AC_SPEED_HIGH, AC_MODE_HEAT)
settings.create(get_time_stamp(), 18, 25, 0.5, AC_SPEED_MEDIUM, AC_MODE_HEAT)
settings.create(get_time_stamp(), 18, 25, 1/3, AC_SPEED_LOW, AC_MODE_HEAT)

settings.create(get_time_stamp(), 18, 28, 1, AC_SPEED_HIGH, AC_MODE_COOL)
settings.create(get_time_stamp(), 18, 28, 0.5, AC_SPEED_MEDIUM, AC_MODE_COOL)
settings.create(get_time_stamp(), 18, 28, 1/3, AC_SPEED_LOW, AC_MODE_COOL)

