import random
from ..config import (
    USER_RESERVATION_RATE, MAP_WIDTH, MAP_HEIGHT
)


class User:
    _id_counter: int = 0
    
    @staticmethod
    def _get_next_id() -> int:
        User._id_counter += 1
        return User._id_counter

    def __init__(self, simulator, time):
        from ..events import reservation_event
        
        # progressive id for each user
        self.user_id = User._get_next_id()
        self.simulator = simulator
        self.reservation_time = None
        
        # Schedule first reservation
        res_time = time + 60 * random.expovariate(USER_RESERVATION_RATE)
        location = (random.uniform(0, MAP_WIDTH), random.uniform(0, MAP_HEIGHT))
        self.reservation_time = res_time
        simulator.schedule_event(res_time, reservation_event, (self, location))
