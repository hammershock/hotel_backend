
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

    def switch(self, state, fan_speed=None):
        """
        设置空调状态
        """
        self.is_on = state
        if self.is_on:
            self.scheduler.add_to_waiting(self)
        else:
            self.scheduler.remove_from_service(self)

        if fan_speed:
            self.fan_speed = fan_speed

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
        时间调度
        """
        # Update time on for ACs in service queue and move them to waiting queue if needed
        for ac in self.service_queue:
            ac.time_on += dt
            if ac.time_on >= self.time_slice:
                self.service_queue.remove(ac)
                self.add_to_waiting(ac)
                ac.reset_time_on()

        # Move ACs from waiting to service queue if there is space
        while len(self.service_queue) < 3 and self.waiting_queue:
            self.service_queue.append(self.waiting_queue.pop(0))  # 取优先级最高的加入

    def step(self, dt):
        """
        时间片轮转，执行调度
        """
        # Update the temperature for all ACs
        for ac in self.service_queue + self.waiting_queue:
            ac.update(dt)

        # Update the queues
        self.update_queues(dt)


scheduler = Scheduler()

acs = [AirConditioner(scheduler, i, temp) for i, temp in enumerate([10, 15, 18, 12, 14], start=1)]


# Add air conditioners to the service queue
for ac in acs:
    scheduler.add_to_service(ac)


on = [[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 1]]

dt = 0.1
# The main loop simulating the time steps
for t, states, fan_speeds in zip(range(30), [[] * 30], [[] * 30]):  # Simulating 10 time steps
    for state, fan_speed, ac in zip(states, fan_speeds, acs):
        ac.switch(state, fan_speed=fan_speed)

    scheduler.step(dt)
    # Print the status of each AC
    for ac in acs:
        print(f"Room {ac.room_id}: Temp - {ac.current_temp:.2f}, Status - {'On' if ac.is_on else 'Off'}")

    # Insert a pause or condition here to receive and process requests

