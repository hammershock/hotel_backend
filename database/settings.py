import os
import sqlite3
from datetime import datetime
from itertools import product
from typing import Optional, Tuple, List, Union


db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../hotel.db'))


def get_time_stamp() -> str:
    current_time = datetime.now()
    timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    return timestamp_str


# 增
def create(timestamp: str, min_temperature: int, max_temperature: int, ac_rate: float, ac_speed: str, ac_mode: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (timestamp, min_temperature, max_temperature, ac_rate, ac_speed, ac_mode) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, min_temperature, max_temperature, ac_rate, ac_speed, ac_mode))
    conn.commit()
    conn.close()


def get_latest_setting(ac_speed: str, ac_mode: str) -> Optional[Tuple[int, str, int, int, float, str, str]]:
    """

    :param ac_speed:
    :param ac_mode:
    :return: setting_id, timestamp, min_temperature, max_temperature, ac_rate
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT setting_id, timestamp, min_temperature, max_temperature, ac_rate FROM settings
        WHERE ac_speed = ? AND ac_mode = ?
        ORDER BY setting_id DESC
        LIMIT 1
    ''', (ac_speed, ac_mode))
    result = cursor.fetchone()

    conn.close()
    return result


def query(
        timestamp: Union[str, tuple[str, str]] = None,
        min_temperature: Union[int, tuple[int, int]] = None,
        max_temperature: Union[int, tuple[int, int]] = None,
        ac_rate: Union[float, tuple[float, float]] = None,
        ac_speed: str = None,
        ac_mode: str = None,
        fetchall: Optional[bool] = None,
        fetchone: Optional[bool] = None
) -> List[Tuple[int, str, int, int, float, str, str]]:
    """
    查询 settings 表，支持多条件过滤
    :return: (setting_id, timestamp, min_temperature, max_temperature, ac_rate, ac_speed, ac_mode)
    """
    query = "SELECT * FROM settings WHERE"
    params = []
    conditions = []

    for field, value in {
        'timestamp': timestamp,
        'min_temperature': min_temperature,
        'max_temperature': max_temperature,
        'ac_rate': ac_rate,
        'ac_speed': ac_speed,
        'ac_mode': ac_mode
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
        settings = cursor.fetchall()
    elif fetchone:
        settings = cursor.fetchone()
    else:
        settings = cursor.fetchall()
    conn.close()
    return settings


if __name__ == "__main__":
    from database.roles import *
    for speed, mode in product([AC_SPEED_LOW, AC_SPEED_MEDIUM, AC_SPEED_HIGH], [AC_MODE_COOL, AC_MODE_HEAT]):
        create(get_time_stamp(), 20, 32, 0.1, speed, mode)
    # print(get_latest_setting(AC_SPEED_HIGH, AC_MODE_HEAT))
    print(query())
    pass
