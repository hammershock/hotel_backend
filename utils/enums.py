from enum import Enum, auto


class QueueState(Enum):
    IDLE = 'IDLE'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'


class Role(Enum):
    customer = 'customer'
    manager = 'manager'
    frontDesk = 'frontDesk'


class AcMode(Enum):
    HEAT = 'HEAT'
    COOL = 'COOL'


class FanSpeed(Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'

