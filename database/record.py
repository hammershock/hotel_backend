import os
import sqlite3
from typing import List, Tuple, Union, Optional

db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../hotel.db'))


def add(
        room_number: int,
        customer_session_id: int,
        room_temperature: float,
        timestamp: str,
        ac_is_on: bool,
        ac_temperature: int,
        ac_speed: str,
        ac_mode: str,
        ac_rate: float
) -> int:
    """
    创建新的房间记录
    :param room_number: 房间号
    :param customer_session_id: 客户会话 ID
    :param room_temperature: 房间温度
    :param timestamp: 时间戳
    :param ac_is_on: 空调状态
    :param ac_temperature: 空调温度
    :param ac_speed: 空调风速
    :param ac_mode: 空调模式
    :param ac_rate: 空调费率
    :return: 创建的房间记录ID
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO room_records (room_number, customer_session_id, room_temperature, timestamp, ac_is_on, ac_temperature, ac_speed, ac_mode, ac_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (room_number, customer_session_id, room_temperature, timestamp, ac_is_on, ac_temperature, ac_speed, ac_mode,
         ac_rate))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


# 查询
def query(
        record_id: Union[int, tuple[int, int]] = None,
        room_number: Union[int, tuple[int, int]] = None,
        customer_session_id: Union[int, tuple[int, int]] = None,
        room_temperature: Union[float, tuple[float, float]] = None,
        timestamp: Union[str, tuple[str, str]] = None,
        ac_is_on: bool = None,
        ac_temperature: Union[int, tuple[int, int]] = None,
        ac_speed: str = None,
        ac_mode: str = None,
        ac_rate: Union[float, tuple[float, float]] = None,
        fetchall=None,
        fetchone=None) -> List[Tuple[int, int, int, float, str, bool, int, str, str, float]]:
    """
    查询 room_records 表，支持多条件过滤
    缺点是容易受到SQL注入攻击，建议使用 ORM（如 SQLAlchemy）来帮助安全地构建查询
    record_id, room_number, customer_session_id, room_temperature, timestamp, ac_is_on, ac_temperature, ac_speed, ac_mode, ac_rate
    其中支持范围索引的属性有:record_id, room_number, customer_session_id, room_temperature, timestamp, ac_temperature, ac_rate
    :param record_id: 记录ID
    :param room_number: 房间号
    :param customer_session_id: 客户会话ID
    :param room_temperature: 房间温度
    :param timestamp: 时间戳
    :param ac_is_on: 空调是否开启
    :param ac_temperature: 空调温度
    :param ac_speed: 空调风速
    :param ac_mode: 空调模式
    :param ac_rate: 空调费率
    :param fetchall
    :param fetchone
    :return: 满足过滤条件的记录列表
    """
    query = "SELECT * FROM room_records WHERE"
    params = []
    conditions = []

    for field, value in {
        'record_id': record_id,
        'room_number': room_number,
        'customer_session_id': customer_session_id,
        'room_temperature': room_temperature,
        'timestamp': timestamp,
        'ac_is_on': ac_is_on,
        'ac_temperature': ac_temperature,
        'ac_speed': ac_speed,
        'ac_mode': ac_mode,
        'ac_rate': ac_rate
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
        records = cursor.fetchall()
    elif fetchone:
        records = cursor.fetchone()
    else:
        records = cursor.fetchall()
    conn.close()

    return records


def get_latest_customer_session_id(room_number: int) -> Optional[int]:
    """
    获取特定房间号的最后一个入住的客户会话ID
    :param room_number: 房间号
    :return: 最后一个客户会话ID或None（如果没有找到记录）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 按照时间戳降序排列并限制结果为一条记录
    cursor.execute("SELECT customer_session_id FROM room_records WHERE room_number = ? ORDER BY timestamp DESC LIMIT 1", (room_number,))
    result = cursor.fetchone()

    conn.close()

    return result[0] if result else None
