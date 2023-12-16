import heapq
import random
import time
import uuid
import threading
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship

from utils.enums import Role, FanSpeed, AcMode, QueueState

import os

from flask import Flask, abort, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy


TIME_EXPIRES = 7  # 7days


app = Flask(__name__)
CORS(app)

app.config['JWT_SECRET_KEY'] = os.urandom(24)  # 配置 JWT
jwt = JWTManager(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
db = SQLAlchemy(app)


class ACScheduler:
    def __init__(self, db, interval=1):
        self.db = db
        self.interval = interval
        self.max_num = 3
        self.running_list = []
        self.waiting_queue = []
        self.last_update = time.time()
        self.cooling_rate = 0.5/60
        self.rate = 1.  # 空调费率

        self.boost = 6.

    def minimum(self, a1, a2):
        return (a1, 0) if a1 < a2 else (a2, 1)

    def get_speed(self, fanSpeed):
        # 每分钟改变：
        if fanSpeed == FanSpeed.HIGH:
            return 1.
        elif fanSpeed == FanSpeed.MEDIUM:
            return 0.5
        else:
            return 1/3

    def remove_from_lists(self, room):
        if room.roomID in self.running_list:
            self.running_list.remove(room.roomID)
        self.waiting_queue = [(priority, t,  roomID) for priority, t, roomID in self.waiting_queue if roomID != room.roomID]

    def initialize(self):
        """
        根据房间的状态恢复内存中的队列状态
        """
        with app.app_context():
            rooms = self.db.session.query(Room).all()
            for room in rooms:
                if room.queueState == QueueState.PENDING:
                    self.add_to_waiting(room)  # 初始化队列状态
                elif room.queueState == QueueState.IDLE:
                    self.remove_from_lists(room)
                else:  # RUNNING
                    self.add_to_waiting(room)  # 初始化队列状态
                    room.queueState = QueueState.PENDING
                    db.session.commit()

    def get_priority(self, acSpeed):
        return {'high': 1, 'medium': 2, 'low': 3}.get(acSpeed.value, 3)

    def add_to_waiting(self, room):
        room.queueState = QueueState.PENDING
        db.session.commit()
        # self.waiting_queue = [(priority, t, room_id) for priority, t, room_id in self.waiting_queue]
        heapq.heappush(self.waiting_queue, (self.get_priority(room.fanSpeed), time.time(), room.roomID))
        if room.roomID in self.running_list:
            self.running_list.remove(room.roomID)
        # 在这里产生详单记录

    def update(self):
        with app.app_context():
            t = time.time()

            # records = db.session.query(RoomRecord).all()
            # print("records: ", len(records))

            rooms = self.db.session.query(Room).all()
            for room in rooms:
                if room.queueState == QueueState.RUNNING:  # 空调开启时
                    if room.roomTemperature > room.acTemperature:  # cooling
                        delta, argmin = self.minimum(room.roomTemperature - room.acTemperature, self.get_speed(room.fanSpeed) * (t - self.last_update) / 60 * self.boost)
                        if argmin == 0:
                            self.add_to_waiting(room)  # 到达目标温度而暂停
                            self.generate_record(room)  # 因到达目标温度产生详单记录
                        room.roomTemperature -= delta
                        room.consumption += delta * self.rate
                        db.session.commit()
                    elif room.roomTemperature < room.acTemperature:  # heating
                        delta, argmin = self.minimum(room.acTemperature - room.roomTemperature, self.get_speed(room.fanSpeed) * (t - self.last_update) / 60 * self.boost)
                        if argmin == 0:
                            self.add_to_waiting(room)  # 到达目标温度而暂停
                            self.generate_record(room)  # 因到达目标温度产生详单记录
                        room.roomTemperature += delta
                        room.consumption += delta * self.rate
                        db.session.commit()
                    else:
                        self.add_to_waiting(room)  # 到达目标温度而暂停
                        self.generate_record(room)  # 因到达目标温度产生详单记录
            # print(self.running_list, self.waiting_queue)

            for roomID in self.running_list:
                room = db.session.query(Room).filter_by(roomID=roomID).one()
                # print(datetime.now() - room.firstRuntime)
                if datetime.now() - room.firstRuntime > timedelta(minutes=2) / self.boost:  # 2min / 6
                    print('over time!')
                    self.add_to_waiting(room)  # 超时而暂停
                    self.generate_record(room)  # 因超时暂停产生详单记录

            for room in rooms:
                if room.queueState != QueueState.RUNNING:  # 空调关闭时
                    if room.roomTemperature > room.initialTemperature:  # 房间的回温逻辑
                        room.roomTemperature = max(room.roomTemperature - self.cooling_rate * (t - self.last_update) * self.boost, room.initialTemperature)
                    else:
                        room.roomTemperature = min(room.roomTemperature + self.cooling_rate * (t - self.last_update) * self.boost, room.initialTemperature)
                    db.session.commit()

            while self.waiting_queue and len(self.running_list) < self.max_num:
                _, _, roomID = heapq.heappop(self.waiting_queue)
                room = self.db.session.query(Room).filter_by(roomID=roomID).one()
                room.queueState = QueueState.RUNNING
                room.firstRuntime = datetime.now()
                room.startTimePoint = datetime.now()
                db.session.commit()
                self.running_list.append(roomID)

            self.last_update = t
            print(self.running_list, self.waiting_queue)

    def generate_record(self, room):
        latest_settings = db.session.query(Setting).order_by(Setting.createTime.desc()).first()
        record = RoomRecord(room.roomID, room.customerSessionID, room.requestTime, room.startTimePoint, datetime.now(), room.fanSpeed, room.acMode, latest_settings.rate, room.consumption - room.lastConsumption, room.consumption)
        room.lastConsumption = room.consumption
        db.session.add(record)
        db.session.commit()

    def turn_off(self, room):
        # PENDING/RUNNING -> IDLE
        room.queueState = QueueState.IDLE
        db.session.commit()
        self.remove_from_lists(room)
        self.generate_record(room)  # 因用户操作关闭空调产生详单记录
        print('turn off!', room.queueState, self.running_list, self.waiting_queue)

    def turn_on(self, room):
        # IDLE -> PENDING
        in_waiting = False
        for p, t, id, in self.waiting_queue:
            if id == room.roomID:
                in_waiting = True
        room.requestTime = datetime.now()  # 添加请求时间
        db.session.commit()
        if room.roomID not in self.running_list and not in_waiting:
            self.add_to_waiting(room)  # 开启空调而加入等待队列
        print('turn on!', room.queueState, self.running_list, self.waiting_queue)

    def schedule_wrapper(self):
        try:
            self.update()
        finally:
            # 安排下一次执行
            threading.Timer(self.interval, self.schedule_wrapper).start()

    def start(self):
        threading.Timer(self.interval, self.schedule_wrapper).start()


scheduler = ACScheduler(db)

scheduler.start()


class Account(db.Model):
    __tablename__ = 'account'
    accountID = Column(Integer, primary_key=True)
    roomID = Column(Integer, ForeignKey('room.roomID'), nullable=True)

    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    idCard = Column(String, nullable=True)
    phoneNumber = Column(String, nullable=True)

    createTime = Column(DateTime, nullable=False)
    room = relationship('Room', backref='accounts')

    def __init__(self, username: str, password: str, role: Role, roomID: int = None, idCard: str = None,
                 phoneNumber: str = None):
        """
        登记入住、创建共享帐号
        """
        self.username = username
        self.password = password
        self.role = role

        assert not (role == Role.customer and roomID is None), "客户帐号在创建时必须指定房间ID"

        self.roomID = roomID
        self.idCard = idCard
        self.phoneNumber = phoneNumber

        self.createTime = datetime.now()


class Room(db.Model):
    __tablename__ = 'room'
    roomID = Column(Integer, primary_key=True)
    roomName = Column(String, unique=True, nullable=False)
    unitPrice = Column(Float, nullable=False)
    roomDescription = Column(String)
    consumption = Column(Float)
    roomTemperature = Column(Float)
    acTemperature = Column(Integer)

    fanSpeed = Column(Enum(FanSpeed))
    acMode = Column(Enum(AcMode))
    initialTemperature = Column(Float)
    queueState = Column(Enum(QueueState))

    firstRuntime = Column(DateTime, nullable=True)  # 在被调度为RUNNING态时必须指定
    startTimePoint = Column(DateTime, nullable=True)  # 在空调调度为RUNNING态和空调风速改变时必须指定
    requestTime = Column(DateTime, nullable=True)  # 在初次请求turn on时指定
    lastConsumption = Column(Float)

    customerSessionID = Column(String, nullable=True)  # 在用户入住时必须指定
    checkInTime = Column(DateTime, nullable=True)  # 在用户入住时必须指定
    # 房间的全部记录，管理员可见
    # 用户可见的部分是与当前房间customerSessionID相同的部分
    # 也可以通过与身份证号相同的部分查看历史记录
    records = relationship('RoomRecord', backref='room')

    def __init__(self, roomName: str, roomDescription: str, unitPrice: float, acTemperature: int, fanSpeed: FanSpeed,
                 acMode: AcMode, initialTemperature: float = None):
        """
        创建房间
                >> room = Room('243', '大床房', acTemperature=30, fanSpeed=FanSpeed.MEDIUM, acMode=AcMode.HEAT)

        """

        self.roomName = roomName
        self.roomDescription = roomDescription
        self.unitPrice = unitPrice

        self.acTemperature = acTemperature  # 指定为管理员默认设置
        self.fanSpeed = fanSpeed  # 指定为管理员默认设置
        self.acMode = acMode  # 指定为管理员默认设置

        self.queueState = QueueState.IDLE

        self.initialTemperature = random.randint(15, 35) if initialTemperature is None else initialTemperature
        self.roomTemperature = self.initialTemperature

        self.consumption = 0.0
        self.firstRuntime = None
        self.customerSessionID = None
        self.lastConsumption = 0.0


class RoomRecord(db.Model):
    __tablename__ = 'room_records'
    id = Column(Integer, primary_key=True)
    roomID = Column(Integer, ForeignKey('room.roomID'))
    customerSessionID = Column(String)
    # 表会只保留过去3年的历史记录
    requestTime = Column(DateTime)
    serveStartTime = Column(DateTime)
    serveEndTime = Column(DateTime)
    fanSpeed = Column(Enum(FanSpeed))
    acMode = Column(Enum(AcMode))
    rate = Column(Float)
    consumption = Column(Float)
    accumulatedConsumption = Column(Float)

    def __init__(self, roomID, customerSessionID, requestTime, serveStartTime, serveEndTime, fanSpeed, acMode, rate,
                 consumption, accumulatedConsumption):
        self.roomID = roomID
        self.customerSessionID = customerSessionID
        self.requestTime = requestTime
        self.serveStartTime = serveStartTime
        self.serveEndTime = serveEndTime
        self.fanSpeed = fanSpeed
        self.acMode = acMode
        self.rate = rate
        self.consumption = consumption
        self.accumulatedConsumption = accumulatedConsumption


class Setting(db.Model):
    __tablename__ = 'settings'
    settingID = Column(Integer, primary_key=True)
    createTime = Column(DateTime)
    rate = Column(Float)
    defaultFanSpeed = Column(Enum(FanSpeed))
    defaultTemperature = Column(Integer)
    minTemperature = Column(Integer)
    maxTemperature = Column(Integer)
    acMode = Column(Enum(AcMode))

    def __init__(self, rate: float, defaultFanSpeed: FanSpeed, defaultTemperature: int, minTemperature: int,
                 maxTemperature: int, acMode: AcMode):
        self.rate = rate
        self.defaultFanSpeed = defaultFanSpeed
        self.defaultTemperature = defaultTemperature
        self.minTemperature = minTemperature
        self.maxTemperature = maxTemperature
        self.acMode = acMode

        self.createTime = datetime.now()


with app.app_context():
    db.create_all()
    # account = Account('222', '222', Role.manager)
    # room = Room('211', '大床房', 300, 25, FanSpeed.MEDIUM, AcMode.HEAT)
    # db.session.add(room)
    # db.session.commit()
    #
    # settings = Setting(1., FanSpeed.MEDIUM, 25, 16, 30, AcMode.HEAT)
    # db.session.add(account)
    # db.session.add(settings)
    # db.session.commit()


scheduler.initialize()

@app.route('/check-in', methods=['POST'])
@app.route('/account/create', methods=['POST'])
@jwt_required()
def create_account():
    """
    [管理员，前台]
    create account(绑定帐号与房间关联) > check-in(额外多一个房间为空的判定)
    前台只能创建客户帐号（办理入住）
    管理员可以创建所有帐号
    # data
        # username
        # password
        # role (前台不可选，管理员可选)
        # idCard (前台必选，管理员可选)
        # phoneNumber (前台必选，管理员可选)
        # roomName (前台必选，管理员可选)
    :return:
    """
    account_id = get_jwt_identity()  # 查询来自的帐号id
    origin_account = db.session.query(Account).filter_by(accountID=account_id).one()
    if origin_account.role == Role.customer:
        abort(401, "Unauthorized")  # 客户无权限访问该api

    data = request.json
    if origin_account.role == Role.frontDesk and data.get('role'):  # 前台不能设定角色，只能创建客户帐号
        abort(401, "Unauthorized")

    role = Role.customer if origin_account.role == Role.frontDesk else Role[data['role']]

    if role == Role.customer and not data.get('roomName'):  # 必须为客户指定房间名
        abort(400, "roomName required")
    elif role != Role.customer and data.get('roomName'):
        abort(400, "roomName can only be allocated to customers")

    if role == Role.customer:
        room = db.session.query(Room).filter_by(roomName=data['roomName']).one_or_none()
        if room is None:
            abort(404, "room not found")
        if len(room.accounts) == 0:
            latest_settings = db.session.query(Setting).order_by(Setting.createTime.desc()).first()
            room.queueState = QueueState.IDLE
            room.fanSpeed = latest_settings.defaultFanSpeed
            room.acMode = latest_settings.acMode
            room.consumption = 0.0
            room.acTemperature = latest_settings.defaultTemperature
            room.customerSessionID = str(uuid.uuid4())
            room.checkInTime = datetime.now()
        elif 'check-in' in request.path:
            abort(403, "room is occupied")
        room_id = room.roomID
    else:
        room_id = None

    try:
        new_account = Account(data['username'], data['password'], role, room_id, data.get('idCard'),
                              data.get('phoneNumber'))
        db.session.add(new_account)
        db.session.commit()
    except KeyError as error:
        abort(400, f'Bad request: {error}')

    return jsonify({"msg": "创建成功"}), 201


@app.route('/accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    """
    [管理员，前台]
    获取所有帐号信息
    管理员可以查看所有的
    前台可以查看所有客户的
    :return:
    """
    account_id = get_jwt_identity()
    origin_role = db.session.query(Account).filter_by(accountID=account_id).one().role
    if origin_role == Role.customer:
        abort(401, "Unauthorized")
    query = db.session.query(Account)
    if origin_role == Role.frontDesk:
        query = query.filter_by(role=Role.customer)  # 前台只能查询所有顾客帐号
    accounts = query.all()
    accounts_info = []
    for a in accounts:
        if a.role == Role.customer:
            room = a.room
            if room is None:
                abort(500, "found invalid customer whose room is invalid.")
            accounts_info.append(dict(username=a.username, roomName=room.roomName, roomDescription=room.roomDescription,
                                      createTime=a.createTime, checkInTime=room.checkInTime,
                                      consumption=room.consumption,
                                      role=a.role.value, idCard=a.idCard, phoneNumber=a.phoneNumber))
        else:
            accounts_info.append(dict(username=a.username, roomName=None, roomDescription=None,
                                      createtime=a.createTime, checkInTime=None, consumption=None,
                                      role=a.role.value, idCard=a.idCard, phoneNumber=a.phoneNumber))

    return jsonify(accounts=accounts_info)


@app.route('/account', methods=['GET', 'POST'])
@app.route('/account/<string:username>', methods=['GET', 'POST'])
@jwt_required()
def account(username=None):
    """
    [客户，前台，管理员]
    GET：
    客户只能查看自己的
    前台能查看客户和自己的
    管理员能查看所有人的，也包括自己的
    (不指定username参数查看自己的)
    POST：
    客户修改自己的帐号密码，需要旧的密码
    前台修改客户和自己的帐号和密码，不需要旧的密码
    管理员需要修改所有人的帐号和密码，不需要旧的密码
    """
    account_request = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one()
    role_request = account_request.role
    if role_request == Role.customer and username is not None:
        abort(403, "customers should not visit other accounts")

    account = account_request if username is None else db.session.query(Account).filter_by(
        username=username).one_or_none()
    if account is None:
        abort(404, "account not found")

    if account.role != Role.customer and role_request == Role.frontDesk and username is not None:  # 前台只有权访问和修改客户的帐号和自己的帐号
        abort(401, "Unauthorized")

    if request.method == 'GET':
        room = account.room
        return jsonify(username=account.username, roomName=None if room is None else room.roomName,
                       roomDescription=None if room is None else room.roomDescription,
                       createTime=account.createTime, checkInTime=None if room is None else room.checkInTime,
                       consumption=None if room is None else room.consumption,
                       role=account.role.value, idCard=account.idCard, phoneNumber=account.phoneNumber)

    elif request.method == 'POST':
        data = request.json
        if account_request.role == Role.customer:  # 客户修改自己的用户名和密码
            if data.get('newUsername'):  # 修改用户名
                account.username = data['newUsername']
            if data.get('password') and data.get('newPassword'):  # 修改密码，需要旧的密码验证
                if data['password'] != account.password:
                    abort(403, "password incorrect")
                account.password = data['newPassword']
        else:
            if data.get('username'):  # 前台和管理员修改密码，不需要旧的密码验证
                account.username = data['username']
            if data.get('password'):
                account.password = data['password']


@app.route('/check-out', methods=['POST'])
@app.route('/account/delete', methods=['POST'])
@jwt_required()
def account_delete():
    """
    [管理员，前台]

    # data
        # roomName 退房+删除所有关联帐号，管理员和前台，只能房间名
        # username 帐号删除, 管理员，只能删非客户帐号
    :return:
    """
    origin_role = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one().role
    if origin_role == Role.customer:
        abort(401, "Unauthorized")  # 客户无权访问

    data = request.json
    if data.get('roomName'):  # 提供房间名，办理退房，管理员和前台可以用于办理退房
        room = db.session.query(Room).filter_by(roomName=data['roomName']).one_or_none()
        if room is None:
            abort(404, "room is already not in use")
        room.customerSessionID = None  # 退房流程
        room.checkInTime = None
        room.queueState = QueueState.IDLE
        room.consumption = 0.0
        accounts = room.accounts
        if len(accounts) == 0:
            abort(404, 'room has not been checked-in yet')
        for account in accounts:  # 删除所有关联帐号
            db.session.delete(account)
        db.session.commit()

    elif data.get('username'):  # 提供帐号，删除帐号，只有管理员能删除非客户帐号
        account = db.session.query(Account).filter_by(username=data['username']).one_or_none()
        if origin_role != Role.manager:
            abort(401, "Unauthorized")  # 除了管理员无法访问
        if account is None:
            abort(404, "username does not exists")
        if account.role == Role.customer:
            abort(403, "Please use checkout for customers")

        db.session.delete(account)
        db.session.commit()

    return jsonify({"msg": "退房成功"}), 201


@app.route('/login', methods=['POST'])
def login():
    """
    parameters:
        - username
        - password
        - role

    responses:
        - token

    raise:
    :return:
    """
    data = request.json
    try:
        role = Role[data['role']]
    except KeyError:
        abort(400, "invalid role")
    result = db.session.query(Account).filter_by(username=data['username'], password=data['password'],
                                                 role=role).one_or_none()
    if result is None:
        abort(404, "wrong username or password")
    # 创建 JWT token
    access_token = create_access_token(identity=result.accountID, expires_delta=timedelta(days=TIME_EXPIRES))
    return jsonify(token=access_token), 200


@app.route('/room/create', methods=['POST'])
@jwt_required()
def room_create():
    """
    [管理员]
    管理员可以创建房间

    # data
        # roomName 房间名称
        # roomDescription 房间描述
        # unitPrice 房间单价

    :return:
    """
    origin_role = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one().role
    if origin_role != Role.manager:
        abort(401, "Unauthorized")

    data = request.json
    latest_settings = db.session.query(Setting).order_by(Setting.createTime.desc()).first()
    new_room = Room(roomName=data['roomName'],
                    roomDescription=data['roomDescription'],
                    unitPrice=data['unitPrice'],
                    acTemperature=latest_settings.defaultTemperature,
                    fanSpeed=latest_settings.defaultFanSpeed,
                    acMode=latest_settings.acMode)
    db.session.add(new_room)
    db.session.commit()

    return jsonify({"msg": "创建成功"}), 201


def room_info(room: Room, require_details=False, for_manager=True):
    if room is None:
        abort(404, "room not found")
    if require_details and room.records is None:
        abort(404, "record not found")
    latest_settings = db.session.query(Setting).order_by(Setting.createTime.desc()).first()
    if require_details:
        if not for_manager:
            records = db.session.query(RoomRecord).filter_by(customerSessionID=room.customerSessionID).all()
        else:
            records = db.session.query(RoomRecord).filter_by(roomID=room.roomID).all()
    else:
        records = None
    timeLeft = (datetime.now() - room.firstRuntime) / timedelta(minutes=2) * scheduler.boost if room.firstRuntime is not None else None
    return dict(roomID=room.roomID, roomName=room.roomName, roomDescription=room.roomDescription,
                roomTemperature=room.roomTemperature, timeLeft=timeLeft, unitPrice=room.unitPrice,
                acTemperature=max(min(room.acTemperature, latest_settings.maxTemperature), latest_settings.minTemperature),
                fanSpeed=room.fanSpeed.value, acMode=latest_settings.acMode.value,
                initialTemperature=room.initialTemperature, queueState=room.queueState.value,
                minTemperature=latest_settings.minTemperature, maxTemperature=latest_settings.maxTemperature,
                firstRunTime=room.firstRuntime, customerSessionID=room.customerSessionID, consumption=room.consumption,
                checkInTime=room.checkInTime, occupied=room.customerSessionID is not None,
                roomDetails=[record_info(record) for record in records] if records is not None else None)


def format(s):
    return str(s).replace(',', '.')


def record_info(record: RoomRecord):
    info = dict(id=record.id, duration=format(record.serveEndTime - record.serveStartTime),
                requestTime=format(record.requestTime), serveStartTime=format(record.serveStartTime), serveEndTime=format(record.serveEndTime),
                fanSpeed=record.fanSpeed.value, acMode=record.acMode.value, rate=record.rate,
                consumption=record.consumption, accumulatedConsumption=record.accumulatedConsumption)
    return info


@app.route('/room', methods=['GET', 'POST'])
@app.route('/room/details', methods=['GET'])
@app.route('/room/<string:roomName>/details', methods=['GET'])
@app.route('/room/<string:roomName>', methods=['GET', 'POST'])
@jwt_required()
def room(roomName=None):
    """
    [客户，前台，管理员]
    客户只能查看自己房间
    前台，管理员可以查看所有房间

    客户可以修改自己房间，仅限空调相关
    管理员可以修改所有房间，包括房间名和描述信息
    前台不能修改任何房间
    POST:
    # data
        # state  # 希望空调达到的状态
        # temperature
        # fanSpeed
    GET:
        # data
            # roomID, roomName, roomDescription, consumption, roomTemperature, acTemperature, fanSpeed, acMode,
            # initialTemperature, queueState, firstRunTime, customerSessionID, checkInTime, occupied
            # roomDetails
                # id, requestTime, serveStartTime, serveEndTime, fanSpeed, acMode, rate, consumption, accumulatedConsumption
    :param roomName: 房间号 (不填则根据客户信息自动导航)
    :return:
    """
    account_request = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one()
    room, role_request = account_request.room, account_request.role

    if role_request != Role.manager and roomName is not None:
        abort(404, "only manager can visit other rooms")
    if role_request != Role.customer and roomName is None:
        abort(404, f"{role_request.value} need param roomName")

    room = room if role_request == Role.customer else db.session.query(Room).filter_by(roomName=roomName).one_or_none()
    if room is None:
        abort(404, f"room {roomName} not found")

    if request.method == 'GET':
        require_details = 'details' in request.path
        roomInfo = room_info(room, require_details=require_details, for_manager=role_request == Role.manager)
        return jsonify(roomInfo=roomInfo), 200

    elif request.method == 'POST':
        data = request.json
        if role_request == Role.frontDesk:
            abort(403, "front-desk should not edit room states")
        latest_settings = db.session.query(Setting).order_by(Setting.createTime.desc()).first()
        if isinstance(data, dict) and len({'acTemperature', 'fanSpeed', 'state'} - set(data.keys())) > 0:  # 检测到空调状态修改请求
            if data.get('acTemperature') and latest_settings.minTemperature < int(data['acTemperature']) < latest_settings.maxTemperature:
                room.acTemperature = int(data['acTemperature'])
            if data.get('fanSpeed'):
                if data['fanSpeed'] in FanSpeed.__dict__.keys() and data['fanSpeed'] != room.fanSpeed.value:  # 风速发生变化
                    room.startTimePoint = datetime.now()
                    scheduler.generate_record(room)  # 因用户操作改变风速产生详单记录
                    room.fanSpeed = FanSpeed[data['fanSpeed']]  # 更新风速信息，并产生详单
            # 检测到空调开关机请求
            if data['acState'] and room.queueState == QueueState.IDLE:
                scheduler.turn_on(room)  # 记录requestTime
            elif not data['acState'] and room.queueState != QueueState.IDLE:
                scheduler.turn_off(room)  # 产生详单

        if role_request != Role.manager and (data.get('roomName') or data.get('roomDescription')):
            abort(401, "Unauthorized")
        if data.get('roomName'):  # 酒店管理员可以修改房间名和房间描述，房间的单价只有在房间创建时才能指定，不能修改
            room.roomName = data['roomName']
        if data.get('roomDescription'):
            room.roomDescription = data['roomDescription']
        db.session.commit()
        return jsonify({"msg": "状态更新成功"}), 201


@app.route('/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    """
    [管理员，前台]
    查看所房间状态
    :return:
    """
    role_request = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one().role
    if role_request == Role.customer:
        abort(401, "Unauthorized")
    rooms = db.session.query(Room).all()
    rooms_info = [room_info(room) for room in rooms]
    return jsonify(roomsInfo=rooms_info), 200


@app.route('/room/delete', methods=['POST'])
@jwt_required()
def delete_room():
    """
    [管理员]
    删除房间
    # data
        # roomName
    :return:
    """
    role_request = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one().role
    if role_request != Role.manager:
        abort(401, "Unauthorized")

    room_to_delete = db.session.query(Room).filter_by(roomName=request.json['roomName']).one_or_none()
    if room_to_delete is None:
        abort(404, "room not exists")

    if len(room_to_delete.accounts) > 0:
        abort(401, "room occupied, please check-out first")

    db.session.delete(room_to_delete)
    db.session.commit()
    return jsonify({"msg": "注销成功"}), 201


@app.route('/settings', methods=['POST', 'GET'])
@jwt_required()
def change_settings():
    """
    [管理员]
    查看和修改空调设置
    # data
        # minTemperature
        # maxTemperature
        # defaultTemperature
        # acMode
        # defaultFanSpeed
        # rate
    :return:
    """
    account_request = db.session.query(Account).filter_by(accountID=get_jwt_identity()).one()
    if account_request.role != Role.manager:
        abort(401, "Unauthorized")

    if request.method == 'POST':
        data = request.json
        setting = Setting(rate=data['rate'], defaultFanSpeed=FanSpeed[data['defaultFanSpeed']],
                          defaultTemperature=data['defaultTemperature'], acMode=data['acMode'],
                          minTemperature=data['minTemperature'], maxTemperature=data['maxTemperature'])
        db.session.add(setting)
        db.session.commit()
    else:
        setting = db.session.query(Setting).order_by(Setting.createTime.desc()).first()

    return jsonify(settingID=setting.settingID, lastEditTime=str(setting.createTime), rate=setting.rate,
                   defaultFanSpeed=setting.defaultFanSpeed.value,
                   defaultTemperature=setting.defaultTemperature, minTemperature=setting.minTemperature,
                   maxTemperature=setting.maxTemperature,
                   acMode=setting.acMode.value), 201 if request.method == 'POST' else 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
