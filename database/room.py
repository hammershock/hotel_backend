import os
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
        account_id: int = None
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
    :param account_id: 账号 ID（可选，如果有账号与房间关联）
    :return: 创建的房间记录ID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO room (room_number, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode, account_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (room_number, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed,
         ac_mode, account_id))

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
        account_id: int = None
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
    :param account_id: 账号 ID（可选，如果要关联账号）
    :return: 修改的房间记录数
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = 'UPDATE room SET'
    params = []

    for field, value in {'room_type': room_type, 'room_duration': room_duration,
                         'room_consumption': room_consumption, 'room_temperature': room_temperature,
                         'ac_is_on': ac_is_on, 'ac_temperature': ac_temperature, 'ac_speed': ac_speed,
                         'ac_mode': ac_mode, 'account_id': account_id}.items():
        if value is not None:
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
        account_id: int = None,
        fetchall=None,
        fetchone=None
) -> List[Tuple[int, str, int, float, float, bool, int, str, str, int]]:
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
    :param account_id: 账号 ID（可选，如果要查询与账号关联的房间）
    :param fetchall
    :param fetchone
    :return: (room_number, account_id, room_type, room_duration, room_consumption, room_temperature, ac_is_on, ac_temperature, ac_speed, ac_mode)
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
        'account_id': account_id
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
    else:
        rooms = cursor.fetchone()
    conn.close()

    return rooms


if __name__ == "__main__":
    create(111, '大床房', 1, 0.0, 30, False, 28, 'low', 'heating', 1)
