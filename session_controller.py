from datetime import datetime


class SessionController:

    def __init__(self):
        self.phase = "PRE_MARKET"

    def update(self, current_time):

        if current_time < "09:15":
            self.phase = "PRE_MARKET"

        elif current_time < "09:21":
            self.phase = "DISCOVERY"

        elif current_time < "09:25":
            self.phase = "LOCK_REFERENCE"

        elif current_time < "11:00":
            self.phase = "TREND"

        elif current_time < "13:00":
            self.phase = "MID_SESSION"

        elif current_time < "15:00":
            self.phase = "THETA"

        elif current_time < "15:20":
            self.phase = "GAMMA"

        else:
            self.phase = "CLOSE"

        return self.phase

    def get_phase(self):
        return self.phase
