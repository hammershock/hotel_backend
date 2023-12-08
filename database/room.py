import os
import random
import sqlite3
from typing import List, Tuple, Union


db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../hotel.db'))


# 增
def create(
        room_number: int,
        room_type: str,
        room_duration: int,
        room_consumption: float,
        room_temperature: float,
        ac_is_on: bool,
        ac_temperature: int,
        ac_speed: str,
        ac_mode: str,
        customer_session_id: int,
        account_id: int = None,
        ac_will_on: bool = None,
        time_since_first_on: float = None,
        room_init_temperature: float = None

) -> int:
    """
    创建新的房间记录
    :param room_number: 房间号
    :param room_type: 房间类型
    :param room_duration: 房间持续时间
    :param room_consumption: 房间消费
    :param room_temperature: 房间温度
    :param ac_is_on: 空调状态
    :param ac_temperature: 空调温度
    :param ac_speed: 空调风速
    :param ac_mode: 空调模式
    :param customer_session_id:
    :param ac_will_on 空调开启的意愿
    :param time_since_first_on: 距离刚开始的时间
    :param account_id: 账号 ID（可选，如果有账号与房间关联）
    :param room_init_temperature: 房间初始温度
    :return: 创建的房间记录ID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ac_will, ac_is_on, time_since_on,
    cursor.execute(
        'INSERT INTO room (room_number, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, account_id, customer_session_id, ac_will_on, time_since_first_on, room_init_temperature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (room_number, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed,
         ac_mode, account_id, customer_session_id, ac_will_on, time_since_first_on, room_init_temperature))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


# 删
def delete(room_number: int) -> None:
    """
    删除房间
    :param room_number: 要删除的房间号
    :return:
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM room WHERE room_number = ?', (room_number,))
    conn.commit()
    conn.close()


# 改
def update(
        room_number: int,
        room_type: str = None,
        room_duration: int = None,
        room_consumption: float = None,
        room_temperature: float = None,
        ac_is_on: bool = None,
        ac_temperature: int = None,
        ac_speed: str = None,
        ac_mode: str = None,
        customer_session_id: int = None,
        account_id: int = None,
        ac_will_on: bool = None,
        time_since_first_on: float = None,
        room_init_temperature: float = None,
) -> None:
    """
    修改房间属性
    :param room_number: 要修改的房间号
    :param room_type: 房间类型
    :param room_duration: 房间持续时间
    :param room_consumption: 房间消费
    :param room_temperature: 房间温度
    :param ac_is_on: 空调状态
    :param ac_temperature: 空调温度
    :param ac_speed: 空调风速
    :param ac_mode: 空调模式
    :param customer_session_id: 顾客会话ID
    :param account_id: 账号 ID（可选，如果要关联账号）
    :param ac_will_on 开启空调的意愿
    :param time_since_first_on 距离上次开启空调的时间
    :param room_init_temperature:
    :return: 修改的房间记录数
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'UPDATE room SET'
    params = []

    for field, value in {'room_type': room_type, 'room_duration': room_duration,
                         'room_consumption': room_consumption, 'room_temperature': room_temperature,
                         'ac_is_on': ac_is_on, 'ac_temperature': ac_temperature, 'ac_speed': ac_speed,
                         'ac_mode': ac_mode, 'customer_session_id': customer_session_id, 'account_id': account_id,
                         "ac_will_on": ac_will_on, "time_since_first_on": time_since_first_on,
                         "room_init_temperature": room_init_temperature}.items():
        if value is not None:
            query += f" {field} = ?,"
            params.append(value)

    query = query.rstrip(',')

    query += ' WHERE room_number = ?'
    params.append(room_number)

    cursor.execute(query, params)
    conn.commit()
    conn.close()


def update_kwargs(
        room_number: int,
        **kwargs) -> None:
    """
    修改房间属性
    :param room_number: 要修改的房间号
    :return: 修改的房间记录数
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'UPDATE room SET'
    params = []

    for field, value in kwargs.items():
        query += f" {field} = ?,"
        params.append(value)

    query = query.rstrip(',')

    query += ' WHERE room_number = ?'
    params.append(room_number)

    cursor.execute(query, params)
    conn.commit()
    conn.close()


# 查
def query(
        room_number: Union[int, tuple[int, int]] = None,
        room_type: str = None,
        room_duration: Union[int, tuple[int, int]] = None,
        room_consumption: Union[float, tuple[float, float]] = None,
        room_temperature: Union[float, tuple[float, float]] = None,
        ac_is_on: bool = None,
        ac_temperature: Union[int, tuple[int, int]] = None,
        ac_speed: str = None,
        ac_mode: str = None,
        customer_session_id: int = None,
        account_id: int = None,
        ac_will_on: bool = None,
        time_since_first_on: float = None,
        room_init_temperature: float = None,
        fetchall=None,
        fetchone=None
) -> List[Tuple[int, str, int, float, float, bool, int, str, str, int]] | Tuple[int, str, int, float, float, bool, int, str, str, int]:
    """
    查询 room 表，支持多条件过滤
    :param room_number: 房间号
    :param room_type: 房间类型
    :param room_duration: 房间持续时间
    :param room_consumption: 房间消费
    :param room_temperature: 房间温度
    :param ac_is_on: 空调状态
    :param ac_temperature: 空调温度
    :param ac_speed: 空调风速
    :param ac_mode: 空调模式
    :param customer_session_id: 顾客会话ID
    :param account_id: 账号 ID（可选，如果要查询与账号关联的房间）
    :param ac_will_on:
    :param time_since_first_on
    :param room_init_temperature
    :param fetchall
    :param fetchone
    :return: (room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, customer_session_id, ac_will_on, time_since_first_on, room_initial_temperature)
    """
    query = "SELECT * FROM room WHERE"
    params = []
    conditions = []

    for field, value in {
        'room_number': room_number,
        'room_type': room_type,
        'room_duration': room_duration,
        'room_consumption': room_consumption,
        'room_temperature': room_temperature,
        'ac_is_on': ac_is_on,
        'ac_temperature': ac_temperature,
        'ac_speed': ac_speed,
        'ac_mode': ac_mode,
        'customer_session_id': customer_session_id,
        'account_id': account_id,
        "ac_will_on": ac_will_on,
        "time_since_first_on": time_since_first_on,
        "room_init_temperature": room_init_temperature,
    }.items():
        if value is not None:
            if isinstance(value, tuple):
                # 范围检索
                conditions.append(f"{field} BETWEEN ? AND ?")
                params.extend(value)
            else:
                # 精确匹配
                conditions.append(f"{field} = ?")
                params.append(value)

    # 如果没有提供过滤条件，则移除 WHERE 关键字
    if conditions:
        query += " " + " AND ".join(conditions)
    else:
        query = query.replace(" WHERE", "")

    # 连接到数据库并执行查询
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetchall is None and fetchone is None:
        rooms = cursor.fetchall()
    elif fetchone:
        rooms = cursor.fetchone()
    elif fetchall:
        rooms = cursor.fetchall()
    else:
        rooms = cursor.fetchone()
    conn.close()

    return rooms


def generate_customer_session_id() -> int:
    """
    生成一个用于 customer_session_id 的随机整数
    :return: 随机生成的 customer_session_id
    """
    # 生成一个随机整数，这里的范围可以根据需要调整
    session_id = random.randint(10000, 99999)
    return session_id


# if __name__ == "__main__":
#     create(345, '大床房', 3, 3.0, 31, True, 32, 'high', 'cool', generate_customer_session_id(), 2, ac_will_on=False, time_since_first_on=0.0)
