
class AirConditioner:
    """
    Air Conditioner class representing each room's air conditioner.
    """

    def __init__(self, scheduler, room_id, initial_temp, set_temp=22,):
        self.scheduler = scheduler
        self.room_id = room_id
        self.initial_temp = initial_temp
        self.current_temp = initial_temp
        self.set_temp = set_temp
        self.is_on = False
        self.fan_speed = 'low'  # can be 'low', 'medium', or 'high'
        self.time_on = 0  # Time for which the AC has been on in the current cycle

    def update(self, dt):
        """
        更新房间温度
        """
        if self.is_on:
            if self.fan_speed == 'high':
                change = 1
            elif self.fan_speed == 'medium':
                change = 0.5
            else:  # low speed
                change = 1 / 3
            # Adjust the temperature towards the set temperature
            self.current_temp += change * dt if self.current_temp < self.set_temp else -change * dt
        else:
            # Adjust the temperature towards the initial temperature
            self.current_temp -= 0.5 * dt if self.current_temp > self.initial_temp else 0.5 * dt

    def switch(self, is_on=None, fan_speed=None, set_temp=None):
        """
        设置空调状态
        """
        if is_on is not None:
            self.is_on = is_on

        if fan_speed:
            self.fan_speed = fan_speed

        if set_temp is not None:
            self.set_temp = set_temp

    def reset_time_on(self):
        """
        累计开启时间归零
        """
        self.time_on = 0


class Scheduler:
    """
    Scheduler class to manage air conditioners in service and waiting queues.
    """

    def __init__(self):
        self.service_queue = []
        self.waiting_queue = []
        self.time_slice = 2  # 2 minutes

    def add_to_service(self, ac):
        if len(self.service_queue) < 3:
            self.service_queue.append(ac)
        else:
            self.add_to_waiting(ac)

    def add_to_waiting(self, ac):
        """插入到等待队列的位置保证有序"""
        # Priority: high > medium > low
        index = 0
        for i, waiting_ac in enumerate(self.waiting_queue):
            if self._compare_priority(ac, waiting_ac):  # 如果优先级低，就往后排， 相等的越早越先
                index = i + 1
        self.waiting_queue.insert(index, ac)

    def remove_from_service(self, ac):
        self.waiting_queue.remove(ac)
        self.service_queue.remove(ac)

    @staticmethod
    def _compare_priority(ac1, ac2):
        """
        比较优先级
        """
        priorities = {'high': 3, 'medium': 2, 'low': 1}
        return priorities[ac1.fan_speed] <= priorities[ac2.fan_speed]

    def update_queues(self, dt):
        """
        为使用中的客户计时，超出时间限制就被强行关闭，加入等待队列
        """
        #
        for ac in self.service_queue:
            ac.time_on += dt
            if ac.time_on >= self.time_slice:
                self.service_queue.remove(ac)
                self.add_to_waiting(ac)  # 重新放进优先级队列等待
                ac.reset_time_on()

        # 超时的给等待队列的对头让位
        while len(self.service_queue) < 3 and self.waiting_queue:
            self.service_queue.append(self.waiting_queue.pop(0))

    def step(self, dt):
        """
        时间片轮转，执行调度
        """
        for ac in acs:  # 处理动态逻辑
            ac.update(dt)
        self.update_queues(dt)  # 优先级＋时间片轮转


scheduler = Scheduler()

acs = [AirConditioner(scheduler, i, temp) for i, temp in enumerate([10, 15, 18, 12, 14], start=1)]


# Add air conditioners to the service queue
for ac in acs:
    scheduler.add_to_service(ac)

table = [
    ['开机',None, None, None, None],  # 1min -> 10s
    ['24', '开机',None, None, None],
    [None, None, '开机', None, None],
    [None, '25', None, '开机', '开机'],
    [None, None, '27', None, '高'],
    ['高', None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, '24'],
    [None, None, None, None, None],
    ['28', None, None, '28', '高'],
    [None, None, None, None, None],
    [None, None, None, None, '中'],
    [None, '高', None, None, None],
    [None, None, None, None, None],
    ['关机', None, '低', None, None],
    [None, None, None, None, None],
    [None, None, None, None, '关机'],
    [None, None, '高', None, None],
    ['开机', None, '25，中', None, None],
    [None, None, None, None, None],
    [None, '27，中', None, None, '开机'],
    [None, None, None, None, None],
    [None, None, None, None, None],
    [None, None, None, None, None],
    ['关机', None, '关机', None, '关机'],
    [None, '关机', None, '关机', None],
    [None, None, None, None, None]
]


dt = 1
# The main loop simulating the time steps
for i, states in enumerate(table):  # Simulating 10 time steps
    for state, ac in zip(states, acs):
        ac_state = None
        if state is None:
            continue
        if '开机' in state:
            ac_state = True
        elif '关机' in state:
            ac_state = False

        fan_speed = None
        if '中' in state:
            fan_speed = 'medium'
        elif '低' in state:
            fan_speed = 'low'
        elif '高' in state:
            fan_speed = 'high'

        ac_temperature = None
        if (str(state)[:2]).isdigit():
            ac_temperature = int(str(state)[:2])

        ac.switch(fan_speed=fan_speed, set_temp=ac_temperature)

    scheduler.step(dt)
    # Print the status of each AC
    print([(f"{ac.current_temp:.2f}", ac.is_on) for ac in acs])


    # Insert a pause or condition here to receive and process requests

