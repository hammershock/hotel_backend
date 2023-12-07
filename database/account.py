import os
import sqlite3
from typing import Optional, Tuple, List, Union


db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../hotel.db'))


# 增
def create(username: str, role: str, password: str, room_number: int = None, id_card: str = None, phone_number: str = None) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO account (username, role, password, room_number, id_card, phone_number) VALUES (?, ?, ?, ?, ?, ?)',
                   (username, role, password, room_number, id_card, phone_number
                    ))
    conn.commit()
    account_id = cursor.lastrowid  # 获取最新插入行的 ID
    conn.close()
    return account_id


# 删
def delete(username: str, role: str) -> None:
    """
    删除帐号
    :param username
    :param role
    :return:
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM account WHERE username = ? AND role = ?', (username, role))
    conn.commit()
    conn.close()


# 改
def update(
    account_id: int,
    username: str = None,
    role: str = None,
    password: str = None,
    room_number: int = None,
    id_card: str = None,
    phone_number: str = None
) -> None:
    """
    修改帐号属性
    :param account_id: 要修改的帐号 ID
    :param username: 用户名
    :param role: 角色
    :param password: 密码
    :param room_number: 房间号
    :param id_card: 身份证号
    :param phone_number: 手机号
    :return: None
    """
    conn = sqlite3.connect('../hotel.db')
    cursor = conn.cursor()

    query = 'UPDATE account SET'
    params = []

    for field, value in {'username': username, 'password': password, 'role': role, 'room_number': room_number,
                         'id_card': id_card, 'phone_number': phone_number}.items():
        if value is not None:
            query += f" {field} = ?,"
            params.append(value)

    query = query.rstrip(',')

    query += ' WHERE account_id = ?'
    params.append(account_id)

    cursor.execute(query, params)
    conn.commit()
    conn.close()


# 查
def query(
        account_id: int = None,
        username: str = None,
        role: str = None,
        password: str = None,
        room_number: str = None,
        id_card: str = None,
        phone_number: str = None,
        fetchall=None,
        fetchone=None
) -> Union[List[Tuple[int, str, str, str, str, str]], Optional[Tuple[int, str, str, str, str, str]]]:
    """
    查询 account 表，支持多条件过滤
    :param account_id: 帐号ID
    :param username: 用户名
    :param role: 角色
    :param password: 密码
    :param room_number: 房间号
    :param id_card: 身份证号
    :param phone_number: 手机号
    :param fetchall:
    :param fetchone:
    :return: (account_id, username, password, role, id_card, phone_number) | None | list
    """
    query = "SELECT * FROM account WHERE"
    params = []
    conditions = []

    for field, value in {
        'account_id': account_id,
        'username': username,
        'role': role,
        'room_number': room_number,
        'password': password,
        'id_card': id_card,
        'phone_number': phone_number
    }.items():
        if value is not None:
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
        accounts = cursor.fetchall()
    elif fetchone:
        accounts = cursor.fetchone()
    elif fetchall:
        accounts = cursor.fetchall()
    else:
        accounts = cursor.fetchone()

    conn.close()
    return accounts


if __name__ == "__main__":
    create('111', '客户', '111', 110, '666', '233')
    create('222', '管理员', '222', 111, '777', '724')
    create('333', '前台', '333', 112, '999', '634')

