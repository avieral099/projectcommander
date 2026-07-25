from battle_reference_engine import BattleReference
from session_controller import SessionController
from driver_engine import collect_driver_data


class CommanderEngine:

    def __init__(self):

        self.session = SessionController()

        self.reference = BattleReference()

        self.drivers = {}

        self.evidence = {}

    def update_session(self, current_time):

        return self.session.update(current_time)

    def update_drivers(self):

        self.drivers = collect_driver_data()

        return self.drivers

    def update_evidence(self):

        self.evidence = {

            "battle_reference": self.reference.locked,

            "session": self.session.get_phase(),

            "drivers_loaded": len(self.drivers)

        }

        return self.evidence

    def get_status(self):

        return {

            "session": self.session.get_phase(),

            "battle_reference_locked": self.reference.locked,

            "drivers": len(self.drivers),

            "evidence": self.evidence

        }
